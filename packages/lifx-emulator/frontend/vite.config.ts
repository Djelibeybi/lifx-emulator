import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			adapter: adapter({
				// Output to the FastAPI static directory
				pages: '../src/lifx_emulator_app/api/static',
				assets: '../src/lifx_emulator_app/api/static',
				fallback: 'index.html',
				precompress: false,
				strict: true
			}),
			paths: {
				// Use default paths - FastAPI will serve _app at /_app
				base: ''
			}
		})
	]
});
