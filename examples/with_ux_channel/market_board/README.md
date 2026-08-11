# Market board (ux_dom + ux-channel)

Live ticker with background feeder + manual bump via trusted control attrs.

```bash
uvicorn examples.with_ux_channel.market_board.app:app --host 0.0.0.0 --port 8094
```
