# Upgrade from 0.9.0 to 0.10.0

Version 0.10.0 adds a new DB column in one table. Use this command to adjust your sqlite DB

```bash
sqlite3 threativore.db "ALTER TABLE user_tags ADD COLUMN custom_emoji varchar(2048);"
sqlite3 threativore.db "ALTER TABLE user_tags ADD COLUMN description TEXT;"
```
# Upgrade from 0.8.0 to 0.9.0

Version 0.8.0 adds a new DB column in one table. Use this command to adjust your sqlite DB

```bash
sqlite3 threativore.db "ALTER TABLE user_tags ADD COLUMN flair varchar(2048);"
sqlite3 threativore.db "ALTER TABLE user_tags ADD COLUMN expires datetime;"
```
# Upgrade from 0.7.0 to 0.8.0

Version 0.8.0 adds a new DB column in one table. Use this command to adjust your sqlite DB

```bash
sqlite3 threativore.db "ALTER TABLE users ADD COLUMN email_override varchar(1024) UNIQUE;"
```
# Upgrade from 0.6.0 to 0.7.0

Version 0.6.0 adds a new DB column in one table. Use this command to adjust your sqlite DB

```bash
sqlite3 threativore.db "ALTER TABLE filter_matches ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'COMMENT';"
```
