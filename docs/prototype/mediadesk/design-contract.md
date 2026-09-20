# MediaDesk · Interactive Prototype Design Contract

## Stack & Delivery
- stack: plain HTML + CSS + vanilla JS, hash-routed SPA (single `index.html` + `styles.css` + `mock.js` + `api.js` + `app.js`)
- delivery: pure-static, offline-openable, zero external CDN (icons inline SVG, fonts system)

## Style Tier & Aesthetic
- style: minimal-light (light-gray workbench, indigo accent)
- aesthetic: restrained editorial workbench — clean surfaces, precise spacing, one purple accent
- tone keywords: calm / efficient / high density but breathable

## Design Tokens
- color.primary: `#4f5bd5`  primary-hover:`#3f49c2`
- brand-soft `#eef0fe`  brand-soft-2 `#e3e6fd`
- color.bg: `#eef1f8`  surface: `#ffffff`  surface-2 `#f7f9fe`  surface-3 `#eef1f8`
- border: `#e4e9f2`  border-strong: `#d3dae8`
- text: `#1c2333`  text-sub: `#64748b`  text-faint: `#9aa3bd`
- success `#2f9e54`  danger `#d1495b`  warning `#c98a1b`
- font: `"Microsoft YaHei UI","Segoe UI",system-ui,sans-serif` (system, offline)
- font.scale: 12 / 13 / 14 / 16 / 21 / 28
- radius: sm 9 / md 12 / lg 16
- shadow: sm `0 1px 2px rgba(20,30,60,.05),0 2px 8px rgba(20,30,60,.04)`; md `0 6px 20px rgba(20,30,60,.10)`
- spacing base 4 (4/8/12/16/20/24)
- icon: inline SVG, 16/20px, stroke 1.8, color currentColor (no emoji as icons)
- motion: page-load staggered reveal (`.page` children `animation-delay`), transition `.15s ease`

## Component Spec
- button: `.btn-primary`(fill indigo, :hover darker, :active down) `.btn-ghost`(surface+border, :hover border→primary)
- input/.combo: border `#d3dae8`, radius 9, :hover border-strong, :focus border primary
- module card: white surface, border, radius 12, :hover border→primary + shadow-md + translateY(-1)
- tag/.pill: radius 999, colored bg
- progress bar: 6px, rounded, chunk colored by state
- nav-sidebar: white, 216px fixed, icon+label, .active → brand-soft bg + primary text

## App Shell + Canonical Nav (SPA, single Layout — nav cannot drift)
- one `<aside class="app-nav">` + `<header class="topbar">` + `<main class="app-content">` + `<footer class="statusbar">`
- nav items (frozen order): overview总览 / compress压缩 / cut切割 / concat拼接 / convert转换 / rename整理 / settings设置
- nav active rule: `.app-nav [data-nav]` active when `location.hash` === its key (matched in `app.js` router); single mechanism
- mount: sidebar/topbar/statusbar markup in `index.html` once; views injected into `.app-content` by router

## Page List
- overview总览 | env status strip + 3×2 module cards | cards clickable → nav | → compress/cut/…
- compress压缩 | dropzone + task list + param panel + start | drag&drop + task progress | → settings
- cut切割 | dropzone + cut rows(time segments) + times dialog
- concat拼接 | orderable file list + concat mode
- convert转换 | dropzone + format grid + preset
- rename整理 | plan table + dry-run toggle + apply
- settings设置 | ffmpeg path / gpu / output / concurrency cards

## Mock Schema
- `DB.modules`: [{key,name,badge,desc}]
- `DB.tasks`: globals for running/done/failed counters
- `DB.files` per page (names/sizes)
- api stubs `getModules()/probeEnv()/runCompress(files)` return mock with `delay()`, marked `// TODO replace`