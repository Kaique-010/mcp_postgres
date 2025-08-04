# Script para upload automatico do pacote para PyPI
param(
    [string]$TestPyPI = "false"
)

Write-Host "Iniciando processo de upload para PyPI..." -ForegroundColor Green

# Verificar se estamos no diretorio correto
if (-not (Test-Path "setup.py")) {
    Write-Error "Arquivo setup.py nao encontrado. Execute o script na raiz do projeto."
    exit 1
}

# Verificar se as variaveis de ambiente estao definidas
$pypiToken = $env:PYPI_API_TOKEN
$testPypiToken = $env:TEST_PYPI_API_TOKEN

if (-not $pypiToken) {
    Write-Error "Variavel de ambiente PYPI_API_TOKEN nao encontrada. Defina-a antes de executar o script."
    Write-Host "Exemplo: `$env:PYPI_API_TOKEN = 'seu-token-aqui'" -ForegroundColor Yellow
    exit 1
}

if ($TestPyPI -eq "true" -and -not $testPypiToken) {
    Write-Error "Variavel de ambiente TEST_PYPI_API_TOKEN nao encontrada para Test PyPI."
    Write-Host "Exemplo: `$env:TEST_PYPI_API_TOKEN = 'seu-token-de-teste-aqui'" -ForegroundColor Yellow
    exit 1
}

# Criar arquivo .pypirc no diretorio do usuario
$pypircPath = "$env:USERPROFILE\.pypirc"
$pypircContent = @"
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = $pypiToken

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = $testPypiToken
"@

Write-Host "Criando arquivo de configuracao PyPI..." -ForegroundColor Yellow

# Remover arquivo existente se houver
if (Test-Path $pypircPath) {
    Remove-Item $pypircPath -Force
}

# Criar arquivo sem BOM usando ASCII encoding
[System.IO.File]::WriteAllText($pypircPath, $pypircContent, [System.Text.Encoding]::ASCII)
Write-Host "Arquivo .pypirc criado em: $pypircPath" -ForegroundColor Green

# Instalar ferramentas necessarias
Write-Host "Verificando e instalando dependencias..." -ForegroundColor Yellow
try {
    python -m pip install --upgrade pip
    python -m pip install build twine
    Write-Host "Dependencias instaladas com sucesso!" -ForegroundColor Green
} catch {
    Write-Error "Erro ao instalar dependencias: $_"
    exit 1
}

# Ler versao atual do setup.py
$setupContent = Get-Content "setup.py" -Raw
$versionMatch = [regex]::Match($setupContent, "version\s*=\s*['""]([^'""]+)['""]")

if (-not $versionMatch.Success) {
    Write-Error "Nao foi possivel encontrar a versao no setup.py"
    exit 1
}

$currentVersion = $versionMatch.Groups[1].Value
Write-Host "Versao atual: $currentVersion" -ForegroundColor Cyan

# Perguntar se deve incrementar a versao
$incrementVersion = Read-Host "Deseja incrementar a versao? (y/N)"
if ($incrementVersion -eq "y" -or $incrementVersion -eq "Y") {
    $versionParts = $currentVersion.Split('.')
    if ($versionParts.Length -eq 3) {
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]
        $patch = [int]$versionParts[2]
        
        $patch += 1
        $newVersion = "$major.$minor.$patch"
        
        # Atualizar setup.py
        $newSetupContent = $setupContent -replace "version\s*=\s*['""][^'""]+['""]", "version='$newVersion'"
        Set-Content -Path "setup.py" -Value $newSetupContent -Encoding UTF8
        
        Write-Host "Versao atualizada para: $newVersion" -ForegroundColor Green
    } else {
        Write-Error "Formato de versao invalido: $currentVersion"
        exit 1
    }
}

# Limpar builds anteriores
Write-Host "Limpando builds anteriores..." -ForegroundColor Yellow
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "dist", "build", "*.egg-info"

# Verificar arquivos necessarios
$requiredFiles = @("README.md", "requirements.txt", "LICENSE")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Warning "Arquivo $file nao encontrado"
    }
}

# Construir o pacote
Write-Host "Construindo o pacote..." -ForegroundColor Yellow
python -m build

if ($LASTEXITCODE -ne 0) {
    Write-Error "Erro ao construir o pacote"
    exit 1
}

# Verificar se os arquivos foram criados
$distFiles = Get-ChildItem "dist" -ErrorAction SilentlyContinue
if (-not $distFiles) {
    Write-Error "Nenhum arquivo foi gerado na pasta dist"
    exit 1
}

Write-Host "Arquivos gerados:" -ForegroundColor Green
$distFiles | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Cyan }

# Verificar o pacote
Write-Host "Verificando o pacote..." -ForegroundColor Yellow
python -m twine check dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Error "Erro na verificacao do pacote"
    exit 1
}

# Upload para PyPI usando credenciais do arquivo .pypirc
if ($TestPyPI -eq "true") {
    Write-Host "Fazendo upload para Test PyPI..." -ForegroundColor Yellow
    python -m twine upload --repository testpypi dist/*
} else {
    Write-Host "Fazendo upload para PyPI..." -ForegroundColor Yellow
    python -m twine upload dist/*
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Upload concluido com sucesso!" -ForegroundColor Green
    Write-Host "Pacote disponivel em: https://pypi.org/project/mcp-agent-db/" -ForegroundColor Cyan
    Write-Host "Para instalar: pip install mcp-agent-db" -ForegroundColor Cyan
    
    # Limpar arquivo de credenciais por seguranca (opcional)
    $cleanCredentials = Read-Host "Deseja remover o arquivo .pypirc por seguranca? (y/N)"
    if ($cleanCredentials -eq "y" -or $cleanCredentials -eq "Y") {
        Remove-Item -Path $pypircPath -Force -ErrorAction SilentlyContinue
        Write-Host "Arquivo .pypirc removido por seguranca." -ForegroundColor Yellow
    }
} else {
    Write-Error "Erro no upload"
    exit 1
}