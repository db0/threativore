# Upgrade from 0.5.0 to 0.6.0

Version 0.6.0 adds a new DB column in one table. Use this command to adjust your sqlite DB

```bash
sqlite3 threativore.db "ALTER TABLE filter_matches ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'COMMENT';"
```