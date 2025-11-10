# Time Machine Module Test Runner
# Run all unit tests for the Time Machine implementation

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Time Machine Module - Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Running analysis module tests..." -ForegroundColor Yellow
pytest tests/unit/analysis/ -v --tb=short

Write-Host ""
Write-Host "Running Time Machine agent tests..." -ForegroundColor Yellow
pytest tests/unit/agents/test_time_machine.py -v --tb=short

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running with coverage report..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

pytest tests/unit/analysis/ tests/unit/agents/test_time_machine.py `
  --cov=src.qnwis.analysis `
  --cov=src.qnwis.agents.time_machine `
  --cov-report=term-missing `
  --cov-report=html:htmlcov/time_machine `
  -v

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Test suite complete!" -ForegroundColor Green
Write-Host "Coverage report: htmlcov/time_machine/index.html" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
