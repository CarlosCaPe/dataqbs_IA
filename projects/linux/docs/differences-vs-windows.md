# Key Differences: Windows vs Linux (Pop!_OS)

## File System

| Aspect | Windows | Linux |
|--------|---------|-------|
| **Path separators** | Backslash `\` | Forward slash `/` |
| **Root directory** | `C:\` | `/` |
| **Home directory** | `C:\Users\YourName\` | `/home/yourname/` or `~` |
| **Case sensitivity** | No (file.txt = FILE.TXT) | Yes (file.txt ≠ FILE.TXT) |
| **Hidden files** | File attribute | Filename starts with `.` |
| **Line endings** | CRLF (`\r\n`) | LF (`\n`) |
| **Executable files** | `.exe`, `.bat`, `.cmd` | Any file with execute permission (`chmod +x`) |

## Commands

| Task | Windows | Linux |
|------|---------|-------|
| **List files** | `dir` | `ls` or `ls -la` |
| **Change directory** | `cd` | `cd` |
| **Copy file** | `copy` | `cp` |
| **Move/rename** | `move`, `ren` | `mv` |
| **Delete file** | `del` | `rm` |
| **Delete directory** | `rmdir /s` | `rm -rf` |
| **Print file** | `type` | `cat` |
| **Find files** | `dir /s` | `find` or `grep` |
| **Environment vars** | `set VAR=value` or `$env:VAR = "value"` (PS) | `export VAR=value` |
| **View env var** | `echo %VAR%` or `$env:VAR` (PS) | `echo $VAR` |
| **Path separator** | `;` | `:` |
| **Clear screen** | `cls` | `clear` |
| **Package manager** | `winget`, `choco` | `apt`, `snap`, `flatpak` |

## Python & Development

| Aspect | Windows | Linux |
|--------|---------|-------|
| **Python executable** | `python`, `py` | `python3` |
| **pip** | `pip`, `python -m pip` | `pip3`, `python3 -m pip` |
| **Virtual envs** | Same location as project | Same or in `~/.cache/` (Poetry) |
| **Scripts path** | `Scripts\` in venv | `bin/` in venv |
| **Shell** | PowerShell, CMD | bash, zsh |
| **Poetry cache** | `%LOCALAPPDATA%\pypoetry\` | `~/.cache/pypoetry/` |

## Terminal & Shell

| Feature | Windows | Linux |
|---------|---------|-------|
| **Default shell** | PowerShell, CMD | bash |
| **Config file** | `$PROFILE` (PowerShell) | `~/.bashrc`, `~/.bash_profile` |
| **Paste** | `Ctrl+V` or Right-click | `Ctrl+Shift+V` or Middle-click |
| **Copy** | `Ctrl+C` | `Ctrl+Shift+C` |
| **Interrupt command** | `Ctrl+C` | `Ctrl+C` |
| **Tab completion** | Limited | Extensive |
| **Superuser access** | "Run as Administrator" | `sudo` |

## VS Code

| Feature | Windows | Linux |
|---------|---------|-------|
| **Settings location** | `%APPDATA%\Code\User\` | `~/.config/Code/User/` |
| **Terminal** | PowerShell, CMD | bash |
| **Tasks** | Can use PowerShell | Use bash/sh |
| **Python path** | `python` | `python3` |
| **Default interpreter** | Auto-detected | Must be `python3` |

## Permissions & Security

| Aspect | Windows | Linux |
|--------|---------|-------|
| **File permissions** | ACLs (complex) | User/Group/Other (rwx) |
| **Executable** | `.exe` extension | `chmod +x` permission |
| **Admin rights** | UAC prompt | `sudo` command |
| **Root user** | Administrator account | `root` (should not login as) |
| **View permissions** | Right-click → Properties → Security | `ls -l` |
| **Change permissions** | GUI | `chmod 755 file.sh` |
| **Change owner** | GUI | `chown user:group file` |

## Networking

| Task | Windows | Linux |
|------|---------|-------|
| **IP config** | `ipconfig` | `ip addr` or `ifconfig` |
| **DNS lookup** | `nslookup` | `nslookup` or `dig` |
| **Ping** | `ping` | `ping` (add `-c 4` to limit) |
| **Traceroute** | `tracert` | `traceroute` |
| **Network connections** | `netstat` | `netstat` or `ss` |
| **Firewall** | Windows Firewall | `ufw`, `iptables` |

## Software Installation

| Method | Windows | Linux (Pop!_OS/Ubuntu) |
|--------|---------|------------------------|
| **GUI store** | Microsoft Store | Pop!_Shop, Ubuntu Software |
| **Package manager** | `winget install`, `choco install` | `sudo apt install` |
| **Manual** | Download `.exe`, double-click | Download `.deb`, `sudo dpkg -i` or `sudo apt install ./file.deb` |
| **Update all** | Windows Update | `sudo apt update && sudo apt upgrade` |
| **Flatpak** | N/A | `flatpak install` |
| **Snap** | N/A | `snap install` |

## Git & Development Tools

| Tool | Windows | Linux |
|------|---------|-------|
| **Git** | Git for Windows | Native (`git`) |
| **SSH keys** | `~/.ssh/` (same) | `~/.ssh/` |
| **SSL certs** | Windows cert store | `/etc/ssl/certs/` |
| **Build tools** | Visual Studio, MinGW | `build-essential` package |
| **Make** | Not included | `make` |

## Common Pitfalls for Windows Users

### 1. **Case Sensitivity**
```bash
# Windows: These are the same
cd Documents
cd DOCUMENTS

# Linux: These are DIFFERENT
cd Documents  # ✓ Works
cd DOCUMENTS  # ✗ Error if folder is "Documents"
```

### 2. **Path Separators**
```bash
# Windows
python .\scripts\test.py

# Linux
python ./scripts/test.py
```

### 3. **Execute Permission**
```bash
# Windows: .exe/.bat files run directly
script.bat

# Linux: Need execute permission
chmod +x script.sh  # Make executable first
./script.sh         # Then run
```

### 4. **Admin Rights**
```bash
# Windows
# Run terminal as Administrator, then:
install-something.exe

# Linux
# Use sudo for single command:
sudo apt install something
```

### 5. **Python Command**
```bash
# Windows
python --version
pip install package

# Linux
python3 --version
pip3 install package

# Or create alias in ~/.bashrc:
alias python=python3
alias pip=pip3
```

## Advantages of Linux for Development

### ✅ Better for this project because:
1. **Native Unix tools** - All scripts and commands work without translation
2. **Better package management** - `apt` is more reliable than Windows package managers
3. **No antivirus interference** - Windows Defender often blocks/slows dev tools
4. **Better terminal** - bash is more powerful than PowerShell for automation
5. **Faster I/O** - File operations are generally faster
6. **Better Docker/container support** - Native Linux containers
7. **Resource efficiency** - Lower RAM/CPU usage for same tasks

### ⚠️ Windows still better for:
1. **Office apps** - Microsoft Office (LibreOffice is alternative)
2. **Adobe Creative Suite** - Not available on Linux
3. **Certain games** - Though Steam Proton helps
4. **Corporate VPNs** - Some only have Windows clients
5. **Specific proprietary software**

## Useful Aliases for Windows Users

Add to `~/.bashrc`:

```bash
# Windows-like commands
alias cls='clear'
alias dir='ls -la'
alias copy='cp'
alias move='mv'
alias del='rm'
alias type='cat'

# Python shortcuts  
alias python='python3'
alias pip='pip3'

# Quick navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ~='cd ~'

# Common tasks
alias ll='ls -lah'
alias update='sudo apt update && sudo apt upgrade'
alias ports='sudo netstat -tulpn'
```

## Getting Help

```bash
# Command manual
man ls
man git

# Quick help
ls --help
git --help

# Search for command
apropos search_term

# Which package provides a command
dpkg -S /usr/bin/command
```

## Keyboard Shortcuts

| Action | Windows | Linux |
|--------|---------|-------|
| **Copy** | `Ctrl+C` | `Ctrl+Shift+C` (terminal) or `Ctrl+C` (GUI) |
| **Paste** | `Ctrl+V` | `Ctrl+Shift+V` (terminal) or `Ctrl+V` (GUI) |
| **Terminal** | Win key → type "terminal" | `Ctrl+Alt+T` |
| **Task Manager** | `Ctrl+Shift+Esc` | `System Monitor` or `htop` |
| **Lock screen** | `Win+L` | `Super+L` |
| **Screenshot** | `Win+Shift+S` | `Print Screen` or `Shift+Print Screen` |
| **Window close** | `Alt+F4` | `Alt+F4` |
| **Force quit app** | Task Manager | `xkill` (click on window) |
