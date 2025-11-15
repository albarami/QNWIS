# 🚀 React Migration Execution Script
# This script automates the migration from Chainlit to React + Vite

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("1A", "1B", "1C", "2", "3", "4", "5", "all")]
    [string]$Phase = "1A",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipGitCommit = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "d:\lmis_int"

Write-Host "🚀 QNWIS React Migration Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Phase: $Phase" -ForegroundColor Yellow
Write-Host ""

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor Green
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Git-Commit {
    param(
        [string]$Message,
        [string[]]$Files
    )
    
    if ($SkipGitCommit) {
        Write-Host "⏭️  Skipping git commit (--SkipGitCommit flag set)" -ForegroundColor Yellow
        return
    }
    
    try {
        foreach ($file in $Files) {
            git add $file
        }
        git commit -m $Message
        git push origin main
        Write-Success "Committed: $Message"
    } catch {
        Write-Error "Git commit failed: $_"
    }
}

function Phase-1A {
    Write-Host "`n📦 Phase 1A: Minimal React Setup (3 hours)" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    
    # Step 1.1: Initialize Project
    Write-Step "Step 1.1: Initializing React + Vite project..."
    Set-Location $ProjectRoot
    
    if (Test-Path "qnwis-ui") {
        Write-Host "⚠️  qnwis-ui directory already exists. Skipping initialization." -ForegroundColor Yellow
    } else {
        npm create vite@latest qnwis-ui -- --template react-ts
        Set-Location qnwis-ui
        npm install
        npm install axios @microsoft/fetch-event-source date-fns lucide-react
        npm install -D @types/node tailwindcss postcss autoprefixer
        
        Git-Commit -Message "feat(frontend): initialize React + Vite with TypeScript

- Create Vite project with react-ts template
- Install core dependencies (axios, fetch-event-source, date-fns)
- Install Lucide React for icons
- Install Tailwind CSS for styling

Ref: REACT_MIGRATION_PLAN.md Phase 1A Step 1.1" -Files @("qnwis-ui/")
    }
    
    # Step 1.2: Configure Vite
    Write-Step "Step 1.2: Configuring Vite..."
    $viteConfig = @"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
"@
    Set-Content -Path "qnwis-ui/vite.config.ts" -Value $viteConfig
    
    Git-Commit -Message "config(frontend): configure Vite proxy and path aliases

- Add API proxy to http://localhost:8000
- Configure @ alias for src directory
- Set dev server port to 3000

Ref: REACT_MIGRATION_PLAN.md Phase 1A Step 1.2" -Files @("qnwis-ui/vite.config.ts")
    
    # Step 1.3: TypeScript Types
    Write-Step "Step 1.3: Creating TypeScript types..."
    New-Item -ItemType Directory -Force -Path "qnwis-ui/src/types" | Out-Null
    
    # Copy types file (content too large for inline)
    Write-Host "📝 Create qnwis-ui/src/types/workflow.ts manually" -ForegroundColor Yellow
    
    # Step 1.4: SSE Hook
    Write-Step "Step 1.4: Creating SSE streaming hook..."
    New-Item -ItemType Directory -Force -Path "qnwis-ui/src/hooks" | Out-Null
    Write-Host "📝 Create qnwis-ui/src/hooks/useWorkflowStream.ts manually" -ForegroundColor Yellow
    
    # Step 1.5: MVP Component
    Write-Step "Step 1.5: Creating MVP component..."
    Write-Host "📝 Update qnwis-ui/src/App.tsx manually" -ForegroundColor Yellow
    
    # Step 1.6: Tailwind Setup
    Write-Step "Step 1.6: Setting up Tailwind CSS..."
    Set-Location "$ProjectRoot/qnwis-ui"
    npx tailwindcss init -p
    
    $tailwindConfig = @"
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
"@
    Set-Content -Path "tailwind.config.js" -Value $tailwindConfig
    
    $indexCSS = @"
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-50 text-gray-900;
  }
}

@layer components {
  .prose {
    @apply text-gray-700;
  }
  
  .prose p {
    @apply mb-4;
  }
  
  .prose ul {
    @apply list-disc list-inside mb-4;
  }
  
  .prose strong {
    @apply font-semibold text-gray-900;
  }
}
"@
    Set-Content -Path "src/index.css" -Value $indexCSS
    
    Git-Commit -Message "style(frontend): configure Tailwind CSS

- Initialize Tailwind with PostCSS
- Configure content paths
- Add base styles and utilities

Ref: REACT_MIGRATION_PLAN.md Phase 1A Step 1.6" -Files @("qnwis-ui/tailwind.config.js", "qnwis-ui/src/index.css")
    
    Write-Success "Phase 1A Complete! Next: Create the TypeScript files manually."
}

function Phase-1B {
    Write-Host "`n🏗️  Phase 1B: Component Architecture (6 hours)" -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
    
    Set-Location "$ProjectRoot/qnwis-ui/src"
    
    # Create directory structure
    Write-Step "Creating component directory structure..."
    $dirs = @(
        "components/layout",
        "components/workflow",
        "components/analysis",
        "components/common",
        "features"
    )
    
    foreach ($dir in $dirs) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    
    Write-Success "Component structure created. Implement components manually."
}

function Phase-2 {
    Write-Host "`n🗑️  Phase 2: Chainlit Removal (2 hours)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    Set-Location $ProjectRoot
    
    # Step 4.1: Audit
    Write-Step "Step 4.1: Auditing Chainlit usage..."
    $chainlitFiles = Get-ChildItem -Recurse -Include "*.py" | Select-String -Pattern "chainlit" -List
    
    $auditContent = @"
# Chainlit Audit Report

## Files Using Chainlit
$($chainlitFiles | ForEach-Object { "- $($_.Path)" } | Out-String)

## Dependencies
- pyproject.toml
- requirements.txt

## Configuration Files
- apps/chainlit/
- .env.example (CHAINLIT_* variables)

## Documentation
- README.md
- Various docs/ files
"@
    Set-Content -Path "CHAINLIT_AUDIT.md" -Value $auditContent
    
    Git-Commit -Message "docs(migration): audit Chainlit dependencies

- List all files using Chainlit
- Identify configuration files
- Document removal requirements

Ref: REACT_MIGRATION_PLAN.md Phase 2 Step 4.1" -Files @("CHAINLIT_AUDIT.md")
    
    # Step 4.2: Remove Chainlit app
    Write-Step "Step 4.2: Removing Chainlit application..."
    if (Test-Path "apps/chainlit") {
        Remove-Item -Recurse -Force "apps/chainlit"
        Write-Success "Removed apps/chainlit/"
    }
    
    Git-Commit -Message "remove(chainlit): delete Chainlit application

- Remove apps/chainlit/ directory
- Clean up Chainlit-specific code

Ref: REACT_MIGRATION_PLAN.md Phase 2 Step 4.2" -Files @("apps/")
    
    Write-Success "Phase 2 Complete! Chainlit removed."
}

function Phase-3 {
    Write-Host "`n🚀 Phase 3: Production Deployment (3 hours)" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    
    Set-Location "$ProjectRoot/qnwis-ui"
    
    # Create Dockerfile
    Write-Step "Creating production Dockerfile..."
    $dockerfile = @"
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
"@
    Set-Content -Path "Dockerfile" -Value $dockerfile
    
    Write-Success "Phase 3 setup initiated. Complete Docker and nginx configs manually."
}

function Phase-4 {
    Write-Host "`n🧪 Phase 4: Testing & Validation (4 hours)" -ForegroundColor Cyan
    Write-Host "===========================================" -ForegroundColor Cyan
    
    Set-Location "$ProjectRoot/qnwis-ui"
    
    Write-Step "Installing testing dependencies..."
    npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest jsdom
    npm install -D @playwright/test
    
    Write-Success "Testing dependencies installed. Write tests manually."
}

function Phase-5 {
    Write-Host "`n📚 Phase 5: Documentation (2 hours)" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    
    Write-Step "Creating documentation structure..."
    New-Item -ItemType Directory -Force -Path "$ProjectRoot/docs/frontend" | Out-Null
    
    Write-Success "Documentation structure created. Write docs manually."
}

# Main execution
try {
    switch ($Phase) {
        "1A" { Phase-1A }
        "1B" { Phase-1B }
        "1C" { Write-Host "Phase 1C: Backend integration - Manual implementation required" }
        "2" { Phase-2 }
        "3" { Phase-3 }
        "4" { Phase-4 }
        "5" { Phase-5 }
        "all" {
            Phase-1A
            Phase-1B
            Phase-2
            Phase-3
            Phase-4
            Phase-5
        }
    }
    
    Write-Host "`n✅ Phase $Phase execution complete!" -ForegroundColor Green
    Write-Host "📖 See REACT_MIGRATION_PLAN.md for next steps" -ForegroundColor Cyan
    
} catch {
    Write-Error "Execution failed: $_"
    exit 1
}
