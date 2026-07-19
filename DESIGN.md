# Design

## Visual Theme
Gruvbox Dark - Profissional e Intuitivo.

## Color Palette
```css
:root {
  /* Gruvbox Dark Palette */
  --bg-primary: #282828;
  --bg-secondary: #3c3836;
  --bg-tertiary: #504945;
  
  --fg-primary: #ebdbb2;
  --fg-secondary: #d5c4a1;
  --fg-muted: #a89984;

  --accent-yellow: #d79921;
  --accent-blue: #83a598;
  --accent-green: #b8bb26;
  --accent-red: #fb4934;
  --accent-orange: #fe8019;
  --accent-purple: #d3869b;
  --accent-aqua: #8ec07c;

  /* Semantic */
  --color-primary: var(--accent-yellow);
  --color-secondary: var(--accent-blue);
  --color-background: var(--bg-primary);
  --color-foreground: var(--fg-primary);
  --color-surface: var(--bg-secondary);
  --color-border: var(--bg-tertiary);
  --color-error: var(--accent-red);
  --color-success: var(--accent-green);
}
```

## Typography
- **Fonte principal:** `Inter`, sans-serif
- Letras sem serifa proporcionam leitura técnica e profissional.

## Layout & Spacing
- Base 8px.
- Elementos em blocos (block-based), com padding generoso e bordas ligeiramente arredondadas (2px ou 4px) para manter um visual afiado e limpo.

## Motion
**Estritamente desabilitado.**
- Sem `transition`.
- Sem `animation`.
- Todos os estados (`:hover`, `:focus`, `:active`) devem acontecer instantaneamente (0ms de atraso).
