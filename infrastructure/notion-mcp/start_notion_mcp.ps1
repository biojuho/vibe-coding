param(
    [string]$WorkspaceRoot = [System.IO.Path]::GetFullPath(
        [System.IO.Path]::Combine($PSScriptRoot, "..", "..")
    ),
    [switch]$Check
)

$ErrorActionPreference = "Stop"

function Set-EnvFromFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not [System.IO.File]::Exists($Path)) {
        return $false
    }

    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }

        $match = [System.Text.RegularExpressions.Regex]::Match(
            $trimmed,
            "^\s*(?:NOTION_API_KEY|NOTION_TOKEN)\s*=\s*(.*)\s*$"
        )
        if (-not $match.Success) {
            continue
        }

        $value = $match.Groups[1].Value.Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if ($value.Length -gt 0) {
            [System.Environment]::SetEnvironmentVariable($Name, $value, "Process")
            return $true
        }
    }

    return $false
}

if ($env:NOTION_TOKEN -and -not $env:NOTION_API_KEY) {
    [System.Environment]::SetEnvironmentVariable("NOTION_API_KEY", $env:NOTION_TOKEN, "Process")
}

if (-not $env:NOTION_TOKEN) {
    $candidateEnvFiles = @(
        [System.IO.Path]::Combine($WorkspaceRoot, ".env"),
        [System.IO.Path]::Combine($WorkspaceRoot, "projects", "blind-to-x", ".env")
    )

    foreach ($envFile in $candidateEnvFiles) {
        if (Set-EnvFromFile -Path $envFile -Name "NOTION_TOKEN") {
            break
        }
    }
}

if ($env:NOTION_TOKEN -and -not $env:NOTION_API_KEY) {
    [System.Environment]::SetEnvironmentVariable("NOTION_API_KEY", $env:NOTION_TOKEN, "Process")
}

if ($env:NOTION_API_KEY -and -not $env:NOTION_TOKEN) {
    [System.Environment]::SetEnvironmentVariable("NOTION_TOKEN", $env:NOTION_API_KEY, "Process")
}

if (-not $env:NOTION_TOKEN) {
    [Console]::Error.WriteLine("NOTION_TOKEN or NOTION_API_KEY is not set in process env, .env, or projects/blind-to-x/.env.")
    exit 1
}

if ($Check) {
    [Console]::Out.WriteLine("notion_mcp_launcher_ok")
    exit 0
}

& npx.cmd -y "@notionhq/notion-mcp-server" --transport "stdio"
exit $LASTEXITCODE
