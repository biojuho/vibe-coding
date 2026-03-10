/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                cyber: {
                    pink: '#ff2a6d',
                    blue: '#05d9e8',
                    yellow: '#d1f7ff',
                    bg: '#01012b',
                }
            },
            fontFamily: {
                mono: ['"Space Mono"', 'monospace'],
            }
        },
    },
    plugins: [],
}
