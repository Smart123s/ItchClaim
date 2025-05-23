Automatically claim free games from itch.io

## Install
```bash
pip install ItchClaim
```

## Usage

```bash
itchclaim --login <username> claim
```
This command logs in the user (asks for password if it's ran for the first time), refreshes the list of currently free games, and start claiming the unowned ones.

## Docker

```bash
docker run --rm -v "<path-to-user-session-directory>:/data" ghcr.io/smart123s/itchclaim --login <username> claim
```

## Advanced Usage

### Logging in (via flags)
If you don't have access to an interactive shell, you can provide you password via flags too.

```bash
itchclaim --login <username> --password <password> --totp <2FA code or secret>
```

### Start a never ending process that claims at a schedule
Uses cron syntax. For help, visit [crontab.guru](https://crontab.guru).
Can be useful in docker to create an always running container.
Recommended schedule based on [ItchClaim's online update schedule](https://github.com/Smart123s/ItchClaim/blob/6704228164afa65a6501d5a2375aa2bc0a12e117/.github/workflows/web.yml#L21): `28 0,6,12,18 * * *`.
```bash
itchclaim --login <username> schedule --cron "28 0,6,12,18 * * *"
```

### Load credentials form environment variable
If no credentials are provided via command line arguments, the script checks the following environment variables:
 - `ITCH_USERNAME` (equivalent of `--login <username>` flag)
 - `ITCH_PASSWORD` (equivalent of `--password <password>` flag)
 - `ITCH_TOTP` (equivalent of `--totp <2FA code or secret>` flag)


### Scheduling using docker-compose.yml
Create an always running docker container, that claims new sales on a schedule.
After you see `Logged in as <username>` in the logs, the `ITCH_PASSWORD` and `ITCH_TOTP` environment variables can be removed, as a session gets saved to the volume (`/data`).
```yaml
version: 3.8
services:
  itchclaim:
    image: ghcr.io/smart123s/itchclaim
    container_name: itchclaim
    command: ["schedule", "--cron", "28 0,6,12,18 * * *"]
    volumes:
      - <PATH_TO_ITCHCLAIM_DATA_ON_HOST>:/data:rw
    environment:
      ITCH_USERNAME: "Smart123s"
      ITCH_PASSWORD: "<PASSWORD>"
      ITCH_TOTP: "<TOTP/2FA>"
    restart: unless-stopped
```

### Refresh Library
```bash
itchclaim --login <username> refresh_library
```
Allows you to refresh the locally stored list of owned games. Useful if you have claimed/purchased games since you have started using the script.

### Refresh sale cache

#### Download cached sales from CI (recommended)
```bash
itchclaim refresh_from_remote_cache [--url <url>]
```
ItchClaim collects new sales from itch.io every 6 hours and publishes them on ItchClaim's website. Using this method, sales don't need to be scraped by every user, greatly reducing the load on itch.io generated by the script.
This command also removes expired sales from the user's disk. This command is automatically executed by the `claim` command.

### Download links
```bash
itchclaim [--login <username>] download_urls <game_url>
```
Generate a list of uploaded files and their download URLs for a game. These links have an expiration date. If the game doesn't require claiming, this command can be run without logging in.

## CI Commands

*Note: These commands were created for use on the CI, and are not recommended for general users.*

#### Manually collect sales from itch.io
```bash
itchclaim refresh_sale_cache --dir web/data/ --sales "[1,2,3]" --max_pages -1
```
Request details about every single itch.io sale, and save the $0 ones to the disk.
The initial run can take 12+ hours.

#### Parameters
- **dir:** Output directory
- **sales:** (List[int]): Only refresh the sales specified in this list (Optional)
- **max_pages:** (int): The maximum number of pages to download. Default is -1, which means unlimited (Optional)
- **no_fail:** (bool): Continue downloading sales even if a page fails to load
- **max_not_found_pages:** (int): The maximum number of consecutive pages that return 404 before stopping the execution. Default is 25

### Generate static website
```bash
itchclaim generate_web --dir web/data/ --web_dir web/
```
Generates a static HTML file containing a table of all the sales cached on the disk.
This command was created for use on the CI, and is not recommended for general users.

#### Parameters
- **dir:** Location of the data collected about games, as generated by the `refresh_sale_cache` command
- **web_dir:** The output directory

## FAQ

### Is this legal?
This tools is not affiliated with itch.io. Using it may not be allowed, and may result in your account getting suspended or banned. Use at your own risk.

### Can itch.io detect that I'm using this tool?
Yes. We explicitly let itch.io know that the requests were sent by this tool, using the `user-agent` header. Itch.io doesn't block using non-browser user agents (like some big corporations do), so I think that they deserve to know how their services are being used. If they want to block ItchClaim, blocking this user-agent makes it simple for them. This way, they won't have to implement additional anti-bot technologies, which would make both our and itch.io's life worse.

### Why sales are not downloaded directly from itch.io?
The initial plan was to parse https://itch.io/games/on-sale on each run (it was even implemented in [here](https://github.com/Smart123s/ItchClaim/blob/00ddfa3dfe57c747f09486fd7791f0e1d57347f3/ItchClaim/DiskManager.py#L31-L49)), however, it turns out that only a handful of sales are listed there.
Luckily for us, details about every sale are published at https://itch.io/s/<id\>, where id is a sequentially incremented number. However, downloading data about every single sale published on itch.io generates a lot of load on their servers. To ease the load generated on itch.io by this tool, I've decide to do this scraping only once, on a remote server, and make the data publicly available.

### Can ItchClaim developers see who has access the sale data?
No, ItchClaim doesn't log anything.
When running the claim command, one request is sent to ItchClaim, in order to download a list of the latest active sales. Every request besides that is sent directly to itch.io.
The website is hosted on https://ininet.hu.
The site was previously hosted on GitHub Pages, but the project's cache was wiped on 13 Feb, 2025. After that, it had been decided to use a third-party hosting site, because I didn't want to risk my GitHub account getting banned for abuse.
