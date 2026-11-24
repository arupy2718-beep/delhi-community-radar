# Tests
Run from the app folder (the one containing app.py). No API key and no internet are needed; Open-Meteo is mocked and Claude is mocked or off.
```
pip install -r requirements.txt httpx        # httpx is only needed for the tests
python tests/test_backend.py                 # writes backend_results.json
python tests/make_fixtures.py                # real backend output -> tests/fixtures.json
cd tests && npm i jsdom && node test_frontend.js ../static/index.html    # simulated browser (jsdom); writes frontend_results.json
```
jsdom is a simulated browser: it does NOT render CSS/layout, real Leaflet, real GPS, voice input or touch. Those are listed as NOT TESTED in docs/TEST_REPORT.md.
