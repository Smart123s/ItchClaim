Automatically claim free games from itch.io

## Install
```bash
pip install ItchClaim
```

## Usage

### One-in-all command
```bash
itchclaim --login <username> claim
```
This command logs the user in, refreshes the currently free games, and start claiming the unowned ones.

#### Logging in
If no password is provided via flags, you will be prompted to enter you password. However, if you don't have access to an interactive shell, you can provide you password via flags.

```bash
itchclaim --login <username> --password <password> --totp <2FA code or secret>
```

## Advanced Commands

### Refresh Library
```bash
itchclaim --login <username> refresh_library
```
Allows you to refresh the locally stored list of owned games. Useful if you have claimed/purchased games since you have started using the script.

### Refresh sale cache
```bash
itchclaim refresh_sale_cache
```
Refreshes the local cache of itch.io's sales. Removes expired sales and downloads new ones. This command is automatically executed by the `claim` command.

### Download links
```bash
itchclaim [--login <username>] download_urls
```
Generate a download URL for a game. These links have an expiration date. If the game doesn't require claiming, this command can be run without logging in.
*Note: this command is unfinished and currently only works for games that are present in the local sale cache.*


## FAQ

### Is this legal?
This tools is not affiliated with itch.io. Using it may not be allowed, and may result in your account getting suspended or banned. Use at your own risk.

### Can itch.io detect that I'm using this tool?
Yes. We use the `user-agent` header to explicitly let itch.io know that the requests were sent by this tool.
