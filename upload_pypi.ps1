# auto_version_upload.ps1

# Caminho do setup.py
$setupPath = "setup.py"

# Lê o conteúdo
$content = Get-Content $setupPath

# Regex pra pegar versão atual (ex: version='1.0.1' ou version="1.0.1")
$versionLine = $content | Where-Object { $_ -match 'version\s*=\s*["''](\d+\.\d+\.\d+)["'']' }
if (-not $versionLine) {
    Write-Error "Não achei a linha da versão no setup.py"
    exit 1
}

# Extrai a versão atual
$regex = [regex]'version\s*=\s*["''](\d+)\.(\d+)\.(\d+)["'']'
$match = $regex.Match($versionLine)
if (-not $match.Success) {
    Write-Error "Falha ao extrair versão."
    exit 1
}

$major = [int]$match.Groups[1].Value
$minor = [int]$match.Groups[2].Value
$patch = [int]$match.Groups[3].Value

# Incrementa patch
$patch += 1
$newVersion = "$major.$minor.$patch"
Write-Host "Versão atual: $($match.Value) → Nova versão: $newVersion"

# Atualiza a linha da versão no conteúdo
$newContent = $content -replace 'version\s*=\s*["'']\d+\.\d+\.\d+["'']', "version='$newVersion'"

# Salva o arquivo atualizado
Set-Content -Path $setupPath -Value $newContent

# Limpa dist, build e upload
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist
python -m build
twine upload dist/*
