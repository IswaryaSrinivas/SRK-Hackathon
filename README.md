# Shakti Shield — Final functional prototype

## Run the website (important)
Do NOT double-click `templates/index.html` to launch the application. That opens a local file, not the Flask server.

1. Extract this ZIP into a new folder.
2. Double-click `run_windows.bat`.
3. Keep the terminal window open.
4. Open Chrome and visit: http://127.0.0.1:5000

If the page is blank, check that the browser address begins with `http://127.0.0.1:5000` and not `file:///.../templates/index.html`.

## Features
- Original professional Shakti Shield single-page interface
- Homepage women entrepreneur image (online image; requires internet)
- Account creation/login with server-side password hashing and Flask session
- Business plan persistence endpoint
- Mentor request and community post endpoints
- User-consented Location Safety page: browser asks permission, shows coordinates, opens map, allows copy/share; location is not sent to server or continuously tracked
- Emergency guidance (India 112; women's helpline 181 availability may vary)
- SQLite database created on first run

## Safety and limitations
This is a college/hackathon prototype. Sample mentor/profile content is not identity-verified. Location is requested only after the user clicks and grants browser permission; users should share it only with a trusted contact. The site does not dispatch emergency help. Production deployment needs HTTPS, secure cookie configuration, CSRF protection, rate limits, moderation, reliable backups, and real identity verification.
