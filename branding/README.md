# Branding, by volume

`branding/assets` is mounted over LibreChat's `client/public/assets`, so a
customer's logo never means a rebuilt image and never means a fork. Drop files
here with the names LibreChat expects and they replace the defaults:

| file | where it shows |
|---|---|
| `logo.svg` | the header |
| `favicon-32x32.png`, `favicon-16x16.png` | the browser tab |
| `apple-touch-icon-180x180.png` | an iOS home screen |

An empty directory changes nothing, which is the shipped default.

The two pieces of text are environment, not assets, because they are text:
`APP_TITLE` and `CUSTOM_FOOTER` in `.env`.
