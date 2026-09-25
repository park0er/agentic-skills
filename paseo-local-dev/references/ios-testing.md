# iOS Simulator Testing Reference

Detailed guide for building and testing the Paseo app on iOS simulators.

## Build Pipeline

```
npx expo prebuild --platform ios
    → generates ios/ directory (Podfile, .xcworkspace, etc.)
        → pod install (downloads ~950MB of native deps)
            → xcodebuild (compiles RN + pods, 15-25 min first time)
                → install on simulator
                    → Metro serves JS bundle
```

## Known Gotchas

### 1. CocoaPods Encoding Error

**Symptom**: `Encoding::CompatibilityError` during `pod install`  
**Root cause**: CocoaPods uses `unicode_normalize` which requires UTF-8 locale  
**Fix**: Always prefix pod commands with `LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8`

### 2. System Ruby gem install hangs

**Symptom**: `gem install cocoapods` takes forever on macOS system Ruby 2.6  
**Fix**: Never use system Ruby for CocoaPods. Use `brew install cocoapods`.

### 3. Dev-client vs Production build

The app uses `expo-dev-client` — it builds a development shell that connects to Metro at runtime. First launch shows an Expo onboarding sheet and a "Development Servers" picker. To bypass:

```bash
# Send deep link to auto-connect to Metro:
xcrun simctl openurl "<device>" "exp+voice-mobile://expo-development-client/?url=http://localhost:8081"
```

### 4. Notification permission dialog

The app requests notification permission on first launch, blocking the UI. Pre-grant before launch:

```bash
applesimutils --byId <UDID> --bundle sh.paseo --setPermissions "notifications=YES"
```

### 5. Programmatic UI interaction limitations

| Method | Works? | Notes |
|--------|--------|-------|
| `xcrun simctl openurl` | ✅ | Deep links for navigation |
| `applesimutils --setPermissions` | ✅ | Pre-grant before launch |
| `cliclick` | ⚠️ | Requires Accessibility permission |
| `osascript` key events | ⚠️ | Requires Accessibility permission |
| `xcrun simctl ui alert` | ❌ | Not available on modern Xcode |
| XCUITest | ✅ | Full power, but needs a test target |

**Recommended approach**: Use deep links for navigation, `applesimutils` for permissions, and manual/screenshot verification for visual checks.

### 6. Simulator device selection

```bash
# List available devices:
xcrun simctl list devices available | grep iPhone

# Get UDID of a booted device:
xcrun simctl list devices booted -j | python3 -c "
import json,sys
d=json.load(sys.stdin)
for rt,devs in d['devices'].items():
  for dev in devs:
    if dev['state']=='Booted':
      print(f\"{dev['name']}: {dev['udid']}\")
"
```

### 7. Incremental rebuilds

After the first full build, subsequent changes only rebuild the JS bundle (via Metro hot reload) — no need to rebuild native unless:
- `package.json` dependencies changed (new native module)
- `app.config.ts` / `app.json` changed
- Native code in `ios/` was modified

To force a clean native rebuild:
```bash
rm -rf packages/app/ios
npx expo prebuild --platform ios
cd ios && env LANG=en_US.UTF-8 pod install && cd ..
npx expo run:ios --device "iPhone 17"
```

## Verification Checklist

After build + launch, confirm:

- [ ] App shows Paseo home screen (logo + cards)
- [ ] Deep link to agent route renders messages + composer
- [ ] Model picker shows correct provider (e.g. "Kiro default")
- [ ] ⋮ menu is present (fork entry for capable providers)
- [ ] No red screen / crash

## Screenshot for Evidence

```bash
xcrun simctl io "<device>" screenshot /tmp/paseo-ios-verify.png
```
