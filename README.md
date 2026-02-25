# Fabric / Power BI Workspace Manager

GitHub Actions + Python scripts to **create** and **delete** Microsoft Fabric / Power BI workspaces securely.

## Workflows

- **Create Workspaces**  
  Create multiple workspaces with DEV/UAT/PRD suffixes  
  Select environments via checkboxes  
  Assign admins (optional)

- **Delete Workspaces**  
  Delete exact workspace names provided at runtime

## Features

- Service principal authentication (Azure AD App Registration)
- No `.env` files committed
- Secrets & variables managed in GitHub
- Exact-match deletion (safe & explicit)


## Prerequisites & Permissions

1. **Azure App Registration** (Service Principal):
   - **Application permissions**: `Workspace.ReadWrite.All` (grant admin consent)
   - **No delegated permissions** needed for this client-credentials flow

2. **Fabric / Power BI Admin Portal** (Tenant settings → Developer settings):
   - **Service principals can create workspaces, connections, and deployment pipelines**  
     → Enable for the entire organization or a specific security group that includes your service principal.  
     → Required for creating workspaces via API (see: https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer)
   - **Service principals can call Fabric public APIs**  
     → Enable similarly (fallback/related setting in some tenants)

   A **Fabric admin** (or Power BI admin) must enable these. Without them, you'll get 401 Unauthorized errors.

3. **Workspace-level access** (after creation):
   - The service principal automatically becomes a member/owner when it creates the workspace.
   - For admins: Add via `ADMIN_EMAILS` or manually in the portal.

## GitHub Configuration

### Repository Variables (Settings → Secrets and variables → Actions → Variables)

- `AZURE_TENANT_ID`  
  Example: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

- `AZURE_CLIENT_ID`  
  Example: `yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy`

### Repository Secrets (Settings → Secrets and variables → Actions → Secrets)

- `AZURE_CLIENT_SECRET`  
  Example: `App-reg-secret-abc123-def456-ghi789...`

- `ADMIN_EMAILS` (optional – comma-separated)  
  Example: `john.doe@company.com,jane.smith@company.com`

- `FABRIC_CAPACITY_ID` (optional – full Azure resource ID)  
  Example: `/subscriptions/12345678-90ab-cdef-1234-567890abcdef/resourceGroups/rg-fabric/providers/Microsoft.Fabric/capacities/fab-prd-f64`

## How to Use

### Create Workspaces

1. Actions → **Create Fabric / Power BI Workspaces** → Run workflow
2. Enter base names: `Sales,Finance,HR`
3. Check desired environments (DEV / UAT / PRD)
4. Run

### Delete Workspaces

1. Actions → **Delete Specific Fabric / Power BI Workspaces** → Run workflow
2. Enter full names: `sandbox dev,sandbox uat,sandbox production`
3. Run

## Security

- Client secret stored as GitHub secret
- Deletion only affects explicitly listed workspaces

Questions or improvements? Open an issue.