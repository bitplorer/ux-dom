- **Behaviour: `sms:` and `data:image/avif` URLs are allowed.** Neither can run
  script. `data:image/svg+xml`, `blob:`, `ftp:` and custom schemes stay
  refused (ADR 0002, amendment for #86).
- **Behaviour: a scheme-relative `srcset` candidate (`//host/a.png 2x`) is
  refused**, as it already was in `src` (#86).
