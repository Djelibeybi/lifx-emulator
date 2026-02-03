import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
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
	}
};

export default config;
