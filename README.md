# Paper MC systemd scripts

Steps for using the provided scripts and setting up the __Paper MC__ server as a __systemd__ service.  This will allow you to control the server with `systemctl` and interact with it using the `minecraft` command.

-----

## Create Service Account

Create a user account named `minecraft`.  This will be the service account for running the server.
```
sudo useradd -m -r minecraft
sudo passwd minecraft
```

## Download Paper MC

Log into the minecraft service account.  Download __Paper__ server from:
<https://papermc.io/software/paper>

Place the server in `/home/minecraft/papermc` then rename the __Paper__ server executable file to `server.jar`.

Using the commands below, replacing for the correct download URL and filename:
```
mkdir papermc
cd papermc
wget https://api.papermc.io/v2/projects/paper/GETLATESTFROMWEBSITE
mv paper-x.xx.x-xxx.jar server.jar
```

*Note:* If this is the first time you're running __Paper__ on your server, you'll want to manually run it at this point to agree to its EULA.

Run:
```
java -Xms4G -Xmx4G -jar server.jar --nogui
```
On the first run the server writes an `eula.txt` file (with `eula=false`) and exits immediately. Open `eula.txt`, change the line to `eula=true` to accept the [Minecraft EULA](https://aka.ms/MinecraftEULA), then start the server again to generate the world and `server.properties`.

## Configure scripts

Switch back to your primary account with __sudo__ access.

Clone this repo:
```
git clone https://github.com/AtomicSponge/paper-systemd.git
cd paper-systemd
```

Make the scripts executable and symlink them into `/usr/local/bin`:
```
chmod 555 minecraft-console.py minecraft
sudo ln -s "$(pwd)/minecraft-console.py" /usr/local/bin/minecraft-console
sudo ln -s "$(pwd)/minecraft" /usr/local/bin/minecraft
```

Copy the Java options file to the server directory:
```
cp minecraft_java.env /home/minecraft/papermc/minecraft_java.env
```

Place files `minecraft.service` and `minecraft-stdin.socket` in `/etc/systemd/system`:
```
sudo cp minecraft.service /etc/systemd/system
sudo cp minecraft-stdin.socket /etc/systemd/system
sudo systemctl daemon-reload
```

Then to start the service run:
```
sudo systemctl enable --now minecraft
```

The command socket (`/run/minecraft.stdin`) is restricted to the `minecraft` user and group so that other local users can't inject server commands. To run the `minecraft` and `minecraft-console` commands from your own account, add it to the `minecraft` group (log out and back in for it to take effect):
```
sudo usermod -aG minecraft "$USER"
```

## Memory Setting

Default memory setting is 4GB, to change edit `minecraft_java.env` and update `JAVA_OPTS` to your desired values::
```
-Xms4096M -Xmx4096M
```

## Usage

Commands are passed to the server via the provided script `minecraft-console.py`.

To run commands, open console by running `minecraft-console`. 

After executing the command, you will see the server log from `journalctl` and a prompt to enter the command.

To exit the console, press CTRL+C

<sub>*Note:* Do not use / before the command name</sub>

To view server output use the `journalctl` command.

For example, this will monitor the log:
```
journalctl -u minecraft -f
```

-----

## Socket Activation (on-demand startup)

`socket-activate` is a TCP proxy that starts `minecraft.service` the moment a player connects and can stop it automatically after a period of inactivity. With this setup, PaperMC doesn't need to run 24/7.

### Install socket-activate

Available on the AUR as `socket-activate`, or build from source:
<https://github.com/cherti/socket-activate>

### Configure PaperMC to bind on localhost only

In `server.properties`, set:
```
server-ip=127.0.0.1
```

This is required because `socket-activate` will own the public port (25565). If PaperMC also tries to bind on all interfaces, the two will conflict.

### Install and enable the socket activation units

Copy the two new unit files to `/etc/systemd/system`:
```
sudo cp socket-activate-minecraft.socket /etc/systemd/system
sudo cp socket-activate-minecraft.service /etc/systemd/system
sudo systemctl daemon-reload
```

Disable the server from starting at boot (it will now start on demand), then enable the proxy socket:
```
sudo systemctl disable minecraft
sudo systemctl enable --now socket-activate-minecraft.socket
```

### Caveats

**Startup latency:** PaperMC takes 30–60 seconds to start. The first connection attempt may fail or time out while it initialises; subsequent connections work normally.

**Inactivity timeout:** After no players have been connected for 15 minutes, PaperMC is stopped automatically. To change the timeout, edit the `-t` flag in `socket-activate-minecraft.service`. To disable automatic shutdown, remove the `-t` option entirely.

-----

### References

For a list of server commands see:
<https://minecraft.fandom.com/wiki/Commands>

Service script is using the Aikar's flags from:
<https://docs.papermc.io/misc/tools/start-script-gen>

`journalctl` manual:
<https://www.freedesktop.org/software/systemd/man/latest/journalctl.html#>

Adapted from:
<https://unix.stackexchange.com/a/612118>
