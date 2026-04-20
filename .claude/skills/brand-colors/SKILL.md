---
name: brand-colors
description: Use when creating or updating CLI/UI visuals so the official mem color palette and gradient stay consistent across implementations.
---

# Brand Colors

Use this skill whenever you add or change any visual element in the CLI.

## Official palette

- Pink, start: `#E93A7D`
- Coral, transition 1: `#F25C5C`
- Orange, transition 2: `#F98C2B`
- Yellow, final clarity: `#F7B500`

## Official gradient

Use this gradient as the default brand background or highlight treatment:

```css
background: linear-gradient(
  90deg,
  #E93A7D 0%,
  #F25C5C 35%,
  #F98C2B 65%,
  #F7B500 100%
);
```

## Rules

1. Do not invent new brand colors unless the task explicitly requires it.
2. Keep the gradient order unchanged.
3. Use the palette consistently across headers, accents, buttons, highlights, and splash screens.
4. If a component needs a single accent color, choose the color that matches its state or emphasis, but stay within this palette.

