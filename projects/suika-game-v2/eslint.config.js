import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";

export default defineConfig([
	globalIgnores(["dist", "node_modules", "public/sw.js"]),
	{
		files: ["src/**/*.js"],
		extends: [js.configs.recommended],
		languageOptions: {
			ecmaVersion: "latest",
			sourceType: "module",
			globals: { ...globals.browser },
		},
		rules: {
			"no-unused-vars": [
				"error",
				{
					argsIgnorePattern: "^_",
					varsIgnorePattern: "^_",
					caughtErrorsIgnorePattern: "^_",
				},
			],
		},
	},
	{
		files: ["src/**/*.test.js"],
		languageOptions: {
			globals: { ...globals.browser, ...globals.node },
		},
	},
	{
		files: ["scripts/**/*.js", "vite.config.js", "eslint.config.js"],
		languageOptions: {
			sourceType: "module",
			globals: { ...globals.node },
		},
	},
]);
