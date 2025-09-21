#!/usr/bin/env python3
"""
Octagon Staffing Plan Generator — Smart Azure setup that detects existing resources
Requirements:
  - Azure CLI installed and logged in:  az login
  - Python 3.8+
Usage:
  python3 smart_setup.py
  python3 smart_setup.py --debug  # verbose Azure CLI output
"""

import argparse
import json
import os
import random
import string
import subprocess
import sys
import time
from typing import Tuple, Optional, Dict

# ========= SAME CONFIG AS BEFORE =========
SUBSCRIPTION_ID = "54c49ae7-9fed-4a14-91fb-f126b79a0cd6"
BASE = "octagon-staffing"
LOCATION = "eastus2"
OPENAI_LOCATION = "eastus"
DI_SKU = "S0"
SEARCH_SKU = "basic"
ACR_SKU = "Basic"
APP_IMAGE = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
# ==============================

# Fixed names (no random suffixes for these)
RG = f"{BASE}-rg"
KV = f"{BASE}-kv"
DI_NAME = f"{BASE}-docintel"
AOAI_NAME = f"{BASE}-aoai"
CAE = f"{BASE}-cae"
APP_NAME = f"{BASE}-api"
LAW_NAME = f"{BASE}-log"

DEBUG = False

def log(msg: str, level: str = "INFO"):
    timestamp = time.strftime("%H:%M:%S")
    if level == "ERROR":
        print(f"[{timestamp}] ❌ {msg}", file=sys.stderr)
    elif level == "WARN":
        print(f"[{timestamp}] ⚠️  {msg}")
    elif level == "SUCCESS":
        print(f"[{timestamp}] ✅ {msg}")
    elif level == "DEBUG":
        if DEBUG:
            print(f"[{timestamp}] 🔍 {msg}")
    else:
        print(f"[{timestamp}] ℹ️  {msg}")

def step_banner(step_name: str, step_num: int = None):
    prefix = f"Step {step_num}: " if step_num else ""
    print(f"\n{'='*60}")
    print(f"{prefix}{step_name}")
    print('='*60)
    return time.time()

def step_complete(start_time: float, msg: str = ""):
    duration = time.time() - start_time
    suffix = f" - {msg}" if msg else ""
    log(f"Completed in {duration:.1f}s{suffix}", "SUCCESS")

def run(cmd: list, expect_json: bool = False, allow_fail: bool = False) -> Tuple[int, Optional[dict | str]]:
    cmd_str = ' '.join(cmd)
    log(f"Running: {cmd_str}", "DEBUG")
    
    if DEBUG and cmd[0] == "az":
        cmd.extend(["--verbose"])
    
    try:
        start = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        duration = time.time() - start
        
        log(f"Command completed in {duration:.1f}s (exit code: {res.returncode})", "DEBUG")
        
        if res.returncode != 0 and not allow_fail:
            log(f"Command failed: {cmd_str}", "ERROR")
            if res.stderr:
                log(f"STDERR: {res.stderr}", "ERROR")
            if res.stdout:
                log(f"STDOUT: {res.stdout}", "DEBUG")
            sys.exit(res.returncode)
        
        out = res.stdout.strip()
        if expect_json:
            try:
                return res.returncode, json.loads(out) if out else {}
            except json.JSONDecodeError as e:
                log(f"Failed to parse JSON: {e}", "WARN")
                return res.returncode, {}
        return res.returncode, out
        
    except FileNotFoundError:
        log("Azure CLI not found. Please install it: https://learn.microsoft.com/cli/azure/install-azure-cli", "ERROR")
        sys.exit(1)

def get_existing_resources() -> Dict[str, Optional[str]]:
    """Scan the resource group and identify existing resources"""
    start = step_banner("Scanning Existing Resources", 1)
    
    # Check if resource group exists
    code, _ = run(["az", "group", "show", "-n", RG], allow_fail=True)
    if code != 0:
        log(f"Resource group {RG} not found - will create fresh", "WARN")
        step_complete(start, "No existing resources")
        return {}
    
    log(f"Found resource group: {RG}")
    
    # Get all resources in the group
    _, resources_json = run(["az", "resource", "list", "-g", RG], expect_json=True)
    
    resources = {
        'storage': None,
        'keyvault': None,
        'docintel': None,
        'search': None,
        'aoai': None,
        'acr': None,
        'cae': None,
        'app': None,
        'law': None
    }
    
    for resource in resources_json:
        name = resource.get('name', '')
        type_parts = resource.get('type', '').split('/')
        resource_type = type_parts[-1].lower() if type_parts else ''
        
        # Map resource types to our categories
        if resource_type == 'storageaccounts':
            resources['storage'] = name
            log(f"Found storage account: {name}")
        elif resource_type == 'vaults' and 'keyvault' in resource.get('type', '').lower():
            resources['keyvault'] = name
            log(f"Found key vault: {name}")
        elif resource_type == 'accounts' and 'cognitive' in resource.get('type', '').lower():
            if 'formrecognizer' in resource.get('kind', '').lower():
                resources['docintel'] = name
                log(f"Found document intelligence: {name}")
            elif 'openai' in resource.get('kind', '').lower():
                resources['aoai'] = name
                log(f"Found azure openai: {name}")
        elif resource_type == 'searchservices':
            resources['search'] = name
            log(f"Found search service: {name}")
        elif resource_type == 'registries' and 'container' in resource.get('type', '').lower():
            resources['acr'] = name
            log(f"Found container registry: {name}")
        elif resource_type == 'managedenvironments':
            resources['cae'] = name
            log(f"Found container apps environment: {name}")
        elif resource_type == 'containerapps':
            resources['app'] = name
            log(f"Found container app: {name}")
        elif resource_type == 'workspaces' and 'operationalinsights' in resource.get('type', '').lower():
            resources['law'] = name
            log(f"Found log analytics workspace: {name}")
    
    step_complete(start, f"Found {len([v for v in resources.values() if v])} existing resources")
    return resources

def get_or_create_storage(existing_name: Optional[str]) -> Tuple[str, str, str]:
    """Get existing storage or create new one"""
    if existing_name:
        start = step_banner("Using Existing Storage Account", 2)
        log(f"Using existing storage account: {existing_name}")
        
        _, blob_endpoint = run(["az", "storage", "account", "show", "-g", RG, "-n", existing_name, "--query", "primaryEndpoints.blob", "-o", "tsv"])
        _, stg_id = run(["az", "storage", "account", "show", "-g", RG, "-n", existing_name, "--query", "id", "-o", "tsv"])
        
        # Ensure containers exist
        log("Ensuring containers exist...")
        run(["az", "storage", "container", "create", "--account-name", existing_name, "-n", "incoming", "--auth-mode", "login"], allow_fail=True)
        run(["az", "storage", "container", "create", "--account-name", existing_name, "-n", "parsed", "--auth-mode", "login"], allow_fail=True)
        
        step_complete(start, f"Using storage at {blob_endpoint.strip()}")
        return existing_name, blob_endpoint.strip(), stg_id.strip()
    else:
        start = step_banner("Creating Storage Account", 2)
        stg_name = f"{BASE.replace('-', '')}stg{random.randint(1000, 9999)}"
        log(f"Creating new storage account: {stg_name}")
        
        run(["az", "storage", "account", "create", "-g", RG, "-n", stg_name, "-l", LOCATION, "--sku", "Standard_LRS", "--kind", "StorageV2"])
        
        log("Creating blob containers: incoming, parsed")
        run(["az", "storage", "container", "create", "--account-name", stg_name, "-n", "incoming", "--auth-mode", "login"])
        run(["az", "storage", "container", "create", "--account-name", stg_name, "-n", "parsed", "--auth-mode", "login"])
        
        _, blob_endpoint = run(["az", "storage", "account", "show", "-g", RG, "-n", stg_name, "--query", "primaryEndpoints.blob", "-o", "tsv"])
        _, stg_id = run(["az", "storage", "account", "show", "-g", RG, "-n", stg_name, "--query", "id", "-o", "tsv"])
        
        step_complete(start, f"Storage ready at {blob_endpoint.strip()}")
        return stg_name, blob_endpoint.strip(), stg_id.strip()

def get_or_create_keyvault(existing_name: Optional[str]) -> Tuple[str, str]:
    """Get existing Key Vault or create new one"""
    if existing_name:
        start = step_banner("Using Existing Key Vault", 3)
        log(f"Using existing Key Vault: {existing_name}")
        _, kv_id = run(["az", "keyvault", "show", "-g", RG, "-n", existing_name, "--query", "id", "-o", "tsv"])
        step_complete(start, "Key Vault ready")
        return existing_name, kv_id.strip()
    else:
        start = step_banner("Creating Key Vault", 3)
        log(f"Creating Key Vault: {KV} with RBAC authorization")
        
        # Register provider if needed
        run(["az", "provider", "register", "--namespace", "Microsoft.KeyVault", "--wait"])
        
        run(["az", "keyvault", "create", "-g", RG, "-n", KV, "-l", LOCATION, "--sku", "standard", "--enable-rbac-authorization", "true"])
        _, kv_id = run(["az", "keyvault", "show", "-g", RG, "-n", KV, "--query", "id", "-o", "tsv"])
        
        # Grant current user permissions
        log("Granting Key Vault permissions to current user...")
        _, user_id = run(["az", "account", "show", "--query", "user.name", "-o", "tsv"])
        run(["az", "role", "assignment", "create", "--assignee", user_id, "--role", "Key Vault Secrets Officer", "--scope", kv_id])
        
        step_complete(start, "Key Vault ready")
        return KV, kv_id.strip()

def get_or_create_docintel(existing_name: Optional[str]) -> Tuple[str, str]:
    """Get existing Document Intelligence or create new one"""
    if existing_name:
        start = step_banner("Using Existing Document Intelligence", 4)
        log(f"Using existing Document Intelligence: {existing_name}")
        _, endpoint = run(["az", "cognitiveservices", "account", "show", "-g", RG, "-n", existing_name, "--query", "properties.endpoint", "-o", "tsv"])
        _, key = run(["az", "cognitiveservices", "account", "keys", "list", "-g", RG, "-n", existing_name, "--query", "key1", "-o", "tsv"])
        step_complete(start, f"Using endpoint: {endpoint.strip()}")
        return endpoint.strip(), key.strip()
    else:
        start = step_banner("Creating Document Intelligence", 4)
        log(f"Creating Document Intelligence service: {DI_NAME}")
        run(["az", "cognitiveservices", "account", "create", "-g", RG, "-n", DI_NAME, "-l", LOCATION, "--kind", "FormRecognizer", "--sku", DI_SKU, "--yes"])
        
        _, endpoint = run(["az", "cognitiveservices", "account", "show", "-g", RG, "-n", DI_NAME, "--query", "properties.endpoint", "-o", "tsv"])
        _, key = run(["az", "cognitiveservices", "account", "keys", "list", "-g", RG, "-n", DI_NAME, "--query", "key1", "-o", "tsv"])
        
        step_complete(start, f"Document Intelligence ready at {endpoint.strip()}")
        return endpoint.strip(), key.strip()

def get_or_create_search(existing_name: Optional[str]) -> Tuple[str, str]:
    """Get existing Search or create new one"""
    if existing_name:
        start = step_banner("Using Existing Azure AI Search", 5)
        log(f"Using existing Search service: {existing_name}")
        search_endpoint = f"https://{existing_name}.search.windows.net"
        _, search_key = run(["az", "search", "admin-key", "show", "-g", RG, "--service-name", existing_name, "--query", "primaryKey", "-o", "tsv"])
        step_complete(start, f"Using endpoint: {search_endpoint}")
        return search_endpoint, search_key.strip()
    else:
        start = step_banner("Creating Azure AI Search", 5)
        search_name = f"{BASE.replace('-', '')}search{random.randint(1000, 9999)}"
        log(f"Creating Azure AI Search service: {search_name}")
        run(["az", "search", "service", "create", "--name", search_name, "-g", RG, "--location", LOCATION, "--sku", SEARCH_SKU, "--partition-count", "1", "--replica-count", "1"])
        
        search_endpoint = f"https://{search_name}.search.windows.net"
        _, search_key = run(["az", "search", "admin-key", "show", "-g", RG, "--service-name", search_name, "--query", "primaryKey", "-o", "tsv"])
        
        step_complete(start, f"Search service ready at {search_endpoint}")
        return search_endpoint, search_key.strip()

def get_or_create_aoai(existing_name: Optional[str]) -> Tuple[str, str]:
    """Get existing Azure OpenAI or create new one"""
    if existing_name:
        start = step_banner("Using Existing Azure OpenAI", 6)
        log(f"Using existing Azure OpenAI: {existing_name}")
        _, endpoint = run(["az", "cognitiveservices", "account", "show", "-g", RG, "-n", existing_name, "--query", "properties.endpoint", "-o", "tsv"])
        _, key = run(["az", "cognitiveservices", "account", "keys", "list", "-g", RG, "-n", existing_name, "--query", "key1", "-o", "tsv"])
        step_complete(start, f"Using endpoint: {endpoint.strip()}")
        return endpoint.strip(), key.strip()
    else:
        start = step_banner("Creating Azure OpenAI (Optional)", 6)
        log(f"Attempting to create Azure OpenAI: {AOAI_NAME}")
        
        code, _ = run([
            "az", "cognitiveservices", "account", "create",
            "-g", RG, "-n", AOAI_NAME, "-l", OPENAI_LOCATION,
            "--kind", "OpenAI", "--sku", "S0", "--yes"
        ], allow_fail=True)
        
        if code != 0:
            log("Azure OpenAI not available (no access/quota). Will skip.", "WARN")
            step_complete(start, "Skipped - no access")
            return "", ""
        
        _, endpoint = run(["az", "cognitiveservices", "account", "show", "-g", RG, "-n", AOAI_NAME, "--query", "properties.endpoint", "-o", "tsv"])
        _, key = run(["az", "cognitiveservices", "account", "keys", "list", "-g", RG, "-n", AOAI_NAME, "--query", "key1", "-o", "tsv"])
        
        step_complete(start, f"Azure OpenAI ready at {endpoint.strip()}")
        return endpoint.strip(), key.strip()

def save_kv_secrets(kv_name: str, di_ep: str, di_key: str, search_ep: str, search_key: str, aoai_ep: str, aoai_key: str):
    start = step_banner("Storing Secrets in Key Vault", 7)
    
    secrets = [
        ("docintel-endpoint", di_ep),
        ("docintel-key", di_key),
        ("search-endpoint", search_ep),
        ("search-key", search_key)
    ]
    
    if aoai_ep and aoai_key:
        secrets.extend([
            ("aoai-endpoint", aoai_ep),
            ("aoai-key", aoai_key)
        ])
    
    for name, value in secrets:
        log(f"Storing secret: {name}")
        run(["az", "keyvault", "secret", "set", "--vault-name", kv_name, "--name", name, "--value", value])
    
    step_complete(start, f"Stored {len(secrets)} secrets")

def get_or_create_acr(existing_name: Optional[str]) -> Tuple[str, str, str]:
    """Get existing ACR or create new one"""
    if existing_name:
        start = step_banner("Using Existing Container Registry", 8)
        log(f"Using existing ACR: {existing_name}")
        _, login = run(["az", "acr", "show", "-g", RG, "-n", existing_name, "--query", "loginServer", "-o", "tsv"])
        _, acr_id = run(["az", "acr", "show", "-g", RG, "-n", existing_name, "--query", "id", "-o", "tsv"])
        step_complete(start, f"Using ACR: {login.strip()}")
        return existing_name, login.strip(), acr_id.strip()
    else:
        start = step_banner("Creating Container Registry", 8)
        acr_name = f"{BASE.replace('-', '')}acr{random.randint(1000, 9999)}"
        log(f"Creating ACR: {acr_name}")
        run(["az", "acr", "create", "-g", RG, "-n", acr_name, "-l", LOCATION, "--sku", ACR_SKU])
        
        _, login = run(["az", "acr", "show", "-g", RG, "-n", acr_name, "--query", "loginServer", "-o", "tsv"])
        _, acr_id = run(["az", "acr", "show", "-g", RG, "-n", acr_name, "--query", "id", "-o", "tsv"])
        
        step_complete(start, f"ACR ready at {login.strip()}")
        return acr_name, login.strip(), acr_id.strip()

def get_or_create_container_apps_env(existing_name: Optional[str], law_name: str) -> str:
    """Get existing Container Apps Environment or create new one"""
    if existing_name:
        start = step_banner("Using Existing Container Apps Environment", 9)
        log(f"Using existing Container Apps environment: {existing_name}")
        step_complete(start, "Environment ready")
        return existing_name
    else:
        start = step_banner("Creating Container Apps Environment", 9)
        
        log("Installing/updating Container Apps extension...")
        run(["az", "extension", "add", "--name", "containerapp", "--upgrade"], allow_fail=True)
        
        log("Registering Microsoft.App provider...")
        run(["az", "provider", "register", "--namespace", "Microsoft.App", "--wait"])
        
        # Get Log Analytics details
        _, law_cust = run(["az", "monitor", "log-analytics", "workspace", "show", "-g", RG, "-n", law_name, "--query", "customerId", "-o", "tsv"])
        _, law_key = run(["az", "monitor", "log-analytics", "workspace", "get-shared-keys", "-g", RG, "-n", law_name, "--query", "primarySharedKey", "-o", "tsv"])
        
        log(f"Creating Container Apps environment: {CAE}")
        run([
            "az", "containerapp", "env", "create",
            "-g", RG, "-n", CAE, "-l", LOCATION,
            "--logs-destination", "log-analytics",
            "--logs-workspace-id", law_cust.strip(),
            "--logs-workspace-key", law_key.strip()
        ])
        
        step_complete(start, "Container Apps environment ready")
        return CAE

def get_or_create_container_app(existing_name: Optional[str], cae_name: str, blob_endpoint: str) -> Tuple[str, str]:
    """Get existing Container App or create new one"""
    if existing_name:
        start = step_banner("Using Existing Container App", 10)
        log(f"Using existing Container App: {existing_name}")
        
        _, fqdn = run(["az", "containerapp", "show", "-g", RG, "-n", existing_name, "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"])
        
        # Ensure managed identity is assigned
        run(["az", "containerapp", "identity", "assign", "-g", RG, "-n", existing_name, "--system-assigned"], allow_fail=True)
        _, principal = run(["az", "containerapp", "show", "-g", RG, "-n", existing_name, "--query", "identity.principalId", "-o", "tsv"])
        
        step_complete(start, f"Using app at https://{fqdn.strip()}")
        return fqdn.strip(), principal.strip()
    else:
        start = step_banner("Creating Container App", 10)
        
        log(f"Creating Container App: {APP_NAME}")
        _, fqdn = run([
            "az", "containerapp", "create",
            "-g", RG, "-n", APP_NAME,
            "--environment", cae_name,
            "--image", APP_IMAGE,
            "--target-port", "8080", "--ingress", "external",
            "--min-replicas", "1", "--max-replicas", "2",
            "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"
        ])
        
        log("Assigning managed identity...")
        run(["az", "containerapp", "identity", "assign", "-g", RG, "-n", APP_NAME, "--system-assigned"])
        _, principal = run(["az", "containerapp", "show", "-g", RG, "-n", APP_NAME, "--query", "identity.principalId", "-o", "tsv"])
        
        step_complete(start, f"App ready at https://{fqdn.strip()}")
        return fqdn.strip(), principal.strip()

def grant_rbac(principal_id: str, stg_id: str, kv_id: str):
    start = step_banner("Configuring RBAC Permissions", 11)
    
    log("Granting Storage Blob Data Contributor role...")
    run(["az", "role", "assignment", "create", "--assignee", principal_id, "--role", "Storage Blob Data Contributor", "--scope", stg_id], allow_fail=True)
    
    log("Granting Key Vault Secrets User role...")
    run(["az", "role", "assignment", "create", "--assignee", principal_id, "--role", "Key Vault Secrets User", "--scope", kv_id], allow_fail=True)
    
    step_complete(start, "RBAC permissions configured")

def set_container_app_secrets_and_env(app_name: str, di_ep: str, di_key: str, search_ep: str, search_key: str, aoai_ep: str, aoai_key: str, blob_endpoint: str):
    start = step_banner("Configuring App Secrets & Environment", 12)
    
    log("Setting application secrets...")
    run(["az", "containerapp", "secret", "set", "-g", RG, "-n", app_name,
         "--secrets",
         f"di-endpoint={di_ep}", f"di-key={di_key}",
         f"search-endpoint={search_ep}", f"search-key={search_key}"])
    
    if aoai_ep and aoai_key:
        run(["az", "containerapp", "secret", "set", "-g", RG, "-n", app_name,
             "--secrets", f"aoai-endpoint={aoai_ep}", f"aoai-key={aoai_key}"])
    
    log("Configuring environment variables...")
    env_vars = [
        "DOCINTEL_ENDPOINT=secretref:di-endpoint",
        "DOCINTEL_KEY=secretref:di-key",
        "SEARCH_ENDPOINT=secretref:search-endpoint",
        "SEARCH_KEY=secretref:search-key",
        f"STORAGE_BLOB_ENDPOINT={blob_endpoint}"
    ]
    if aoai_ep and aoai_key:
        env_vars.extend(["AOAI_ENDPOINT=secretref:aoai-endpoint", "AOAI_KEY=secretref:aoai-key"])
    
    run(["az", "containerapp", "update", "-g", RG, "-n", app_name, "--set-env-vars", *env_vars])
    
    step_complete(start, "Application configuration complete")

def main():
    global DEBUG
    
    parser = argparse.ArgumentParser(description="Smart Octagon Azure infrastructure setup")
    parser.add_argument("--debug", action="store_true", help="Enable verbose Azure CLI output")
    args = parser.parse_args()
    
    DEBUG = args.debug
    
    script_start = time.time()
    log("Starting smart Octagon setup (detects existing resources)...")
    
    # Set subscription
    run(["az", "account", "set", "--subscription", SUBSCRIPTION_ID])
    
    # Scan for existing resources
    existing = get_existing_resources()
    
    # Get or create all resources
    stg_name, blob_endpoint, stg_id = get_or_create_storage(existing.get('storage'))
    kv_name, kv_id = get_or_create_keyvault(existing.get('keyvault'))
    di_ep, di_key = get_or_create_docintel(existing.get('docintel'))
    search_ep, search_key = get_or_create_search(existing.get('search'))
    aoai_ep, aoai_key = get_or_create_aoai(existing.get('aoai'))
    
    # Store secrets in Key Vault
    save_kv_secrets(kv_name, di_ep, di_key, search_ep, search_key, aoai_ep, aoai_key)
    
    # Container infrastructure
    acr_name, acr_login, acr_id = get_or_create_acr(existing.get('acr'))
    cae_name = get_or_create_container_apps_env(existing.get('cae'), existing.get('law') or LAW_NAME)
    app_fqdn, principal_id = get_or_create_container_app(existing.get('app'), cae_name, blob_endpoint)
    
    # Permissions and configuration
    grant_rbac(principal_id, stg_id, kv_id)
    set_container_app_secrets_and_env(existing.get('app') or APP_NAME, di_ep, di_key, search_ep, search_key, aoai_ep, aoai_key, blob_endpoint)

    total_time = time.time() - script_start
    
    print(f"\n{'='*72}")
    print("✅ SETUP COMPLETE!")
    print(f"Total time: {total_time/60:.1f} minutes")
    print("="*72)
    print(f"Resource Group      : {RG}")
    print(f"Region              : {LOCATION}")
    print()
    print(f"Storage Account     : {stg_name}")
    print(f"  Blob endpoint     : {blob_endpoint}")
    print(f"  Containers        : incoming, parsed")
    print()
    print(f"Key Vault           : {kv_name} (RBAC; secrets saved)")
    print()
    print(f"Doc Intelligence    : {existing.get('docintel') or DI_NAME}")
    print(f"  Endpoint          : {di_ep}")
    print()
    print(f"Azure AI Search     : {existing.get('search') or 'auto-named'}")
    print(f"  Endpoint          : {search_ep}")
    print()
    print(f"Azure OpenAI        : {aoai_ep or '(not created – no access)'}")
    print()
    print(f"Container Registry  : {acr_name}  ({acr_login})")
    print(f"Container Apps Env  : {cae_name}")
    print(f"Container App       : {existing.get('app') or APP_NAME}")
    print(f"  Public URL        : https://{app_fqdn}")
    print()
    print("Next steps:")
    print(f"1) Upload a test SOW PDF into 'incoming':")
    print(f"   az storage blob upload --account-name \"{stg_name}\" --container-name incoming --name sample.pdf --file ./sample.pdf --auth-mode login")
    print()
    print("2) Build & push your app to ACR, then point the Container App to it:")
    print(f"   az acr login -n \"{acr_name}\"")
    print(f"   docker build -t \"{acr_login}/{APP_NAME}:v1\" .")
    print(f"   docker push \"{acr_login}/{APP_NAME}:v1\"")
    print(f"   az containerapp update -g \"{RG}\" -n \"{existing.get('app') or APP_NAME}\" --image \"{acr_login}/{APP_NAME}:v1\"")
    print()
    print("="*72)

if __name__ == "__main__":
    main()