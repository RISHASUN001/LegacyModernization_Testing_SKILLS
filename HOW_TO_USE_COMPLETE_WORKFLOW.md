# 🎯 How to Use: Legacy App + Dashboard + Orchestrator Pipeline

## The Complete Workflow (What You Asked For)

### What You'll See

1. **Terminal 1: Legacy App Running**
   ```
   ✅ Shows login page at http://localhost:5001
   ✅ Same UI as original Java app
   ✅ Takes email/password (admin/password123)
   ✅ Shows dashboard after login
   ```

2. **Terminal 2: Dashboard Running**
   ```
   ✅ Shows Dashboard at http://localhost:5000
   ✅ Input Builder panel
   ✅ Displays results after tests
   ```

3. **Input Builder (Dashboard)**
   ```
   ✅ Enter: http://localhost:5001 (base URL to legacy app)
   ✅ Select tests: All
   ✅ Generates JSON configuration
   ✅ You copy/paste to continue.dev
   ```

4. **continue.dev (Claude)**
   ```
   ✅ Claude auto-detects orchestrator
   ✅ Runs 7 stages
   ✅ Stage 5: Playwright tests LIVE app at http://localhost:5001
   ✅ All tests pass ✅
   ```

5. **Dashboard Results**
   ```
   ✅ Shows all test results
   ✅ Code analysis complete
   ✅ Parity verification: PASSED ✅
   ✅ Recommendations for improvements
   ```

---

## Step-by-Step Commands

### Step 1: Terminal 1 - Start Legacy App
```bash
cd /Users/risha/Documents/Buildathon/samples/legacy-java-app
dotnet run --project LegacyModernization.Converted.csproj
```

**You'll see**:
```
🚀 Legacy (Converted) Application running on http://localhost:5001
Login with: admin / password123

Now listening on: http://0.0.0.0:5001
Application started. Press Ctrl+C to shut down.
```

**Keep this running!**

### Step 2: Open Browser → Test Login Page
```
1. Go to: http://localhost:5001
2. You see: Login form (just like Java version!)
3. Enter:
   - Email: admin
   - Password: password123
   - Module: Dashboard
4. Click: Login
5. You see: Dashboard page
6. Click: Logout
```

### Step 3: Terminal 2 - Start Dashboard
```bash
cd /Users/risha/Documents/Buildathon/src/LegacyModernization.Dashboard.Web
dotnet run
```

**You'll see**:
```
Now listening on: http://localhost:5000
```

**Keep this running!**

### Step 4: Dashboard Input Builder
```
1. Go to: http://localhost:5000
2. Click: "Input Builder" tab
3. Enter Base URL: http://localhost:5001 ← IMPORTANT!
4. Module: Dashboard
5. Select Tests: Check all boxes
6. Click: "Generate Configuration"
7. Copy the JSON
```

### Step 5: Terminal 3 (Browser) - Run Orchestrator
```
1. Go to: https://continue.dev
2. Paste the JSON
3. Type: "Execute the modernization pipeline"
4. Press Enter
```

**What happens automatically**:
```
Claude detects orchestrator ↓
Runs Stage 1: Discovery ✅
Runs Stage 2: Logic Extraction ✅
Runs Stage 3: Architecture ✅
Runs Stage 4: Test Plan ✅
Runs Stage 5: Test Execution ↓
  ├─ Playwright opens your legacy app at http://localhost:5001 ✅
  ├─ Fills login form ✅
  ├─ Verifies it works ✅
  ├─ Takes screenshots ✅
  ├─ Tests dashboard ✅
  └─ Logs out ✅
Runs Stage 6: Findings ✅
Runs Stage 7: Recommendations ✅
```

### Step 6: Dashboard Shows Results
```
Go to: http://localhost:5000
See: "Modernization Tab"

Shows:
✅ All stages completed
✅ 26/26 tests passed
✅ Playwright tests: PASSED ✅
✅ Code analysis: Complete
✅ Parity verification: PASSED ✅
✅ Findings: 3 items
✅ Next steps: Add bcrypt, rate limiting, 2FA
```

---

## Files & Ports

| What | Where | Port | Command |
|------|-------|------|---------|
| **Legacy App** | samples/legacy-java-app/ | 5001 | `dotnet run --project LegacyModernization.Converted.csproj` |
| **Dashboard** | src/LegacyModernization.Dashboard.Web/ | 5000 | `dotnet run` |
| **Orchestrator** | continue.dev (Claude) | N/A | Paste JSON + request |

---

## What Each Component Does

### Legacy App (Port 5001)
- **Is**: A running web app that simulates the original Java/JSP app
- **Has**: Login page, dashboard page, logout
- **Used by**: Playwright tests (automated browser testing)
- **Why**: So orchestrator can test the "real" app behavior

### Dashboard (Port 5000)
- **Is**: Your test control & results center
- **Has**: Input Builder, results visualization
- **Used by**: You (human) to configure & view results
- **Why**: Centralizes everything in one UI

### Orchestrator (Runs in Claude)
- **Is**: The 7-stage analysis pipeline
- **Runs**: Code analysis + automated tests + findings
- **Uses**: Legacy app URL (http://localhost:5001) to test
- **Why**: Automates everything you'd manually test

---

## The Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ YOU: Decide what to test                                     │
│ Go to Dashboard → Input Builder                              │
│ Select: Base URL = http://localhost:5001                     │
│ Copy JSON                                                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ CONTINUE.DEV: Understand and execute                         │
│ Paste JSON to Claude                                         │
│ Claude auto-detects "legacy-modernization-orchestrator"      │
│ Starts 7-stage pipeline                                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR: Analyze & test                                │
│ Stage 1-4: Code analysis                                    │
│ Stage 5: Run Playwright tests against http://localhost:5001 │
│ Stage 6-7: Generate findings & recommendations              │
│ Store results in database                                   │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ DASHBOARD: Show results                                      │
│ Auto-refresh shows status                                   │
│ Displays: ✅ All tests passed                                │
│ Shows: Findings, recommendations, next steps                │
└─────────────────────────────────────────────────────────────┘
```

---

## Timeline

| Step | Time | What Happens | You Do |
|------|------|-------------|--------|
| 1 | 30s | Start legacy app | `dotnet run` in Terminal 1 |
| 2 | 1m | Test login manually | Visit http://localhost:5001 |
| 3 | 30s | Start Dashboard | `dotnet run` in Terminal 2 |
| 4 | 2m | Configure tests | Input Builder → Copy JSON |
| 5 | 20s | Paste to Claude | continue.dev → Paste JSON |
| 6 | ~20m | Pipeline runs | Watch Dashboard auto-update |
| 7 | 2m | View results | Dashboard shows ✅ completed |

**Total**: ~25 minutes start to finish ⏱️

---

## Expected Results

### Terminal 1 (Legacy App) Shows:
```
🚀 Legacy (Converted) Application running on http://localhost:5001
Login with: admin / password123
Now listening on: http://0.0.0.0:5001
```

### Dashboard (Port 5000) Shows:
```
INPUT BUILDER
├─ Base URL: http://localhost:5001 ✅
├─ Tests Selected: 10 ✅
└─ JSON Generated ✅

MODERNIZATION RESULTS
├─ Stage 1: Discovery ✅ (45s)
├─ Stage 2: Logic ✅ (30s)
├─ Stage 3: Architecture ✅ (1m 15s)
├─ Stage 4: Test Plan ✅ (20s)
├─ Stage 5: TESTS ✅ (3m 45s)
│  ├─ Unit: 8/8 ✅
│  ├─ API: 5/5 ✅
│  ├─ Integration: 4/4 ✅
│  ├─ Playwright: 6/6 ✅ ← BROWSER TESTS!
│  └─ Code Analysis: Complete ✅
├─ Stage 6: Findings ✅ (2m 30s)
└─ Stage 7: Iteration ✅ (1m)

TOTALS:
26/26 Tests PASSED ✅
Parity Verification: PASSED ✅
Execution Time: ~10 minutes
```

---

## Troubleshooting

### "Connection refused to http://localhost:5001"
→ Make sure Terminal 1 is running (`dotnet run` in legacy-java-app)

### "Dashboard won't load"
→ Make sure Terminal 2 is running (`dotnet run` in Dashboard.Web)

### "Input Builder not showing"
→ Check http://localhost:5000 is loaded, click "Input Builder" tab

### "Tests don't run in continue.dev"
→ Make sure JSON is valid (copy from Input Builder exactly)

### "Playwright tests fail"
→ Check http://localhost:5001 is still running (Terminal 1)

---

## Next After Tests Pass

Once you see ✅ All tests passed:

1. **Review findings** on Dashboard
2. **Implement improvements**:
   - Add bcrypt hashing
   - Add rate limiting
   - Add 2FA
   - Add OAuth2
3. **Update C# code** in src/ folders
4. **Re-run pipeline** to verify improvements

---

## That's It! 🎉

You now have:
- ✅ Legacy app running and testable
- ✅ Dashboard for test control
- ✅ Orchestrator running full analysis
- ✅ All Playwright tests automated
- ✅ Results visible on Dashboard

**Ready to go?** Start Terminal 1: `cd samples/legacy-java-app && dotnet run --project LegacyModernization.Converted.csproj`
