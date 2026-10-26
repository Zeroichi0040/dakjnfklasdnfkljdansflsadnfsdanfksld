# Open and run

## Windows

Extract all files, then open the extracted `Flask_Fullstack_Framework` folder.
The ZIP is the source distribution; the application runs through Python.

In PowerShell:

```powershell
cd C:\Users\im\Desktop\flasky_website\Flask_Fullstack_Framework
.\SETUP_WINDOWS.bat
```

The launcher checks installed Python 3.11–3.14 runtimes. If it reports a missing
runtime and you have Python Install Manager, run `py install 3.13`; otherwise
install Python 3.13 from [python.org](https://www.python.org/downloads/), then retry.
You can also run the installer directly:

```powershell
py -3.13 scripts\bootstrap.py
# If you already have 3.12, use: py -3.12 scripts\bootstrap.py
```

Setup creates a private `.venv`, installs dependencies, generates unique private
settings in `.env`, applies migrations, and checks readiness. It keeps existing
settings/data when repeated. First installation requires internet.

When you see **SETUP COMPLETE**, press a key when prompted, then run:

```powershell
.\START_WEBSITE.bat
```

Open **http://127.0.0.1:5000**. Create your own account. Keep the terminal open;
Ctrl+C stops the website. Next time, only run `START_WEBSITE.bat`.

## macOS / Linux

With Python 3.12/3.13 installed, open a terminal in the extracted folder:

```sh
bash setup.sh
bash start.sh
```

## Administrator

```powershell
.venv\Scripts\python.exe manage.py create-admin
```

macOS/Linux: `.venv/bin/python manage.py create-admin`. The command privately
prompts for your email/password. Sign in to see administrator tools and Website
pages. New registrations are members; a public signup form cannot choose a role.

## Use the project's Python

Examples in the other guides use `python` after activating `.venv`. Activation:
PowerShell `.\.venv\Scripts\Activate.ps1`; Command Prompt
`.venv\Scripts\activate.bat`; macOS/Linux `source .venv/bin/activate`.
If activation is blocked, directly use `.venv\Scripts\python.exe` instead of changing
your system policy. Restart the server after editing Python. Refresh after changing
templates or static assets. Normal HTML forms still work without JavaScript.

| Problem | Action |
| --- | --- |
| Port unavailable | Run the project Python with `run.py --port 5001`. |
| Migration/readiness error | Run `python manage.py db upgrade`, then `python manage.py check`. |
| CSRF error in an old tab | Reload the form; signing in changes the session/token. |
| No reset email arrives locally | Open the private `.eml` message in `instance/outbox`; it is not sent. |
| Invalid Host / 400 | Use localhost/127.0.0.1 locally; set the real trusted hostname for deployment. |
| Production settings stop setup | Setup installs dependencies but does not silently migrate a production database; apply reviewed migrations explicitly. |

Keep `.env`, database files, outbox messages, and backups private. A fresh extract
is the supported way to start this framework; keep separate applications in separate
directories and environments.
