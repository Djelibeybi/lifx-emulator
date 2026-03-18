# TypeScript / Svelte Code Style Guide

Based on existing project configuration (tsconfig.json, svelte-check).

## TypeScript Configuration

- **Strict mode**: Enabled
- **Module resolution**: `bundler`
- **Verbatim module syntax**: Enabled (explicit `import type` required)
- **Check JS**: Enabled (JavaScript files are also type-checked)
- **Isolated modules**: Enabled

## Svelte 5 Patterns

### Runes (required)

Use Svelte 5 runes throughout — no legacy `$:` reactive declarations or `writable()` stores.

```typescript
// State
let value = $state<Type>(initial);

// Derived (simple expression)
let computed = $derived(expression);

// Derived (complex computation)
let computed = $derived.by(() => { ... });

// Effects
$effect(() => { ... });

// Props
let { prop }: { prop: Type } = $props();
```

### Store Pattern

Custom store factories returning objects with getter accessors:

```typescript
function createMyStore() {
    let value = $state<Type>(initial);

    return {
        get value() { return value; },
        setValue(v: Type) { value = v; }
    };
}

export const myStore = createMyStore();
```

### Component Structure

```svelte
<script lang="ts">
    // 1. Imports
    // 2. Props
    // 3. Local state
    // 4. Derived values
    // 5. Functions
    // 6. Effects
</script>

<!-- Template -->

<style>
    /* Scoped styles */
</style>
```

## CSS

- **Scoped styles** in component `<style>` blocks (Svelte default)
- **Global styles** in `app.css` using CSS custom properties for theming
- **Color output**: Use `oklch()` for color values (perceptually uniform)
- **Theming**: CSS custom properties (`--bg-primary`, `--text-primary`, etc.) with `[data-theme='light']` overrides

## File Organization

```
src/
  app.css              # Global styles + CSS custom properties
  app.html             # HTML shell
  lib/
    components/        # Svelte components
      index.ts         # Barrel exports
    stores/            # Reactive state (.svelte.ts files)
      index.ts         # Barrel exports
    utils/             # Pure functions
    types.ts           # TypeScript interfaces
  routes/
    +page.svelte       # Main page
    +layout.svelte     # Root layout
    +layout.ts         # SSR/prerender config
```

## Build

- **Static adapter**: Builds to `packages/lifx-emulator/src/lifx_emulator_app/api/static/`
- **SSR disabled**: `export const ssr = false`
- **Prerendered**: `export const prerender = true`
