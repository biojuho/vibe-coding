// sharecard.js
//
// Renders the shareable result image on an offscreen canvas. This is the
// visual counterpart to daily.js#buildResultCard (which is plain text) and
// is handed to the Web Share API as a PNG file.

import { FRUITS } from "./config.js";

const CARD_W = 540;
const CARD_H = 720;
const EMOJI_FONT =
	'"Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif';

/**
 * Draw the result card and resolve with a PNG Blob.
 *
 * @param {{challenge:number, score:number, topLevel:number,
 *          streak:number, mode?:string}} r
 * @returns {Promise<Blob>}
 */
export function drawShareCard(r) {
	const { challenge, score, topLevel, streak, mode = "Daily" } = r;
	const canvas = document.createElement("canvas");
	canvas.width = CARD_W;
	canvas.height = CARD_H;
	const ctx = canvas.getContext("2d");

	// Background: warm vertical gradient (the Suika watermelon palette).
	const bg = ctx.createLinearGradient(0, 0, 0, CARD_H);
	bg.addColorStop(0, "#ff8a3d");
	bg.addColorStop(1, "#ff5252");
	ctx.fillStyle = bg;
	ctx.fillRect(0, 0, CARD_W, CARD_H);

	// Rounded inner panel.
	ctx.fillStyle = "rgba(255, 255, 255, 0.94)";
	roundRect(ctx, 30, 30, CARD_W - 60, CARD_H - 60, 28);
	ctx.fill();

	ctx.textAlign = "center";

	// Header watermelon + title.
	ctx.font = `64px ${EMOJI_FONT}`;
	ctx.fillText("🍉", CARD_W / 2, 130);

	ctx.fillStyle = "#222";
	ctx.font = '700 38px "Nunito", sans-serif';
	ctx.fillText(`Suika ${mode}`, CARD_W / 2, 195);

	ctx.fillStyle = "#ff5252";
	ctx.font = '800 30px "Nunito", sans-serif';
	ctx.fillText(`#${challenge}`, CARD_W / 2, 235);

	// Score.
	ctx.fillStyle = "#222";
	ctx.font = '800 84px "Nunito", sans-serif';
	ctx.fillText(score.toLocaleString("en-US"), CARD_W / 2, 345);
	ctx.fillStyle = "#888";
	ctx.font = '600 22px "Nunito", sans-serif';
	ctx.fillText("POINTS", CARD_W / 2, 380);

	// Top fruit reached.
	const top = FRUITS[Math.min(topLevel, FRUITS.length - 1)] || FRUITS[0];
	ctx.font = `90px ${EMOJI_FONT}`;
	ctx.fillText(top.label, CARD_W / 2, 490);
	ctx.fillStyle = "#888";
	ctx.font = '600 20px "Nunito", sans-serif';
	ctx.fillText("최고 과일", CARD_W / 2, 525);

	// Progress bar over the 11-fruit ladder.
	drawProgressBar(ctx, topLevel);

	// Streak.
	if (streak > 0) {
		ctx.fillStyle = "#ff7043";
		ctx.font = '700 26px "Nunito", sans-serif';
		ctx.fillText(`🔥 ${streak}일 연속`, CARD_W / 2, 632);
	}

	// Footer hashtag.
	ctx.fillStyle = "#bbb";
	ctx.font = '600 20px "Nunito", sans-serif';
	ctx.fillText("#SuikaDaily", CARD_W / 2, 672);

	return new Promise((resolve, reject) => {
		canvas.toBlob((blob) => {
			if (blob) resolve(blob);
			else reject(new Error("canvas.toBlob produced no blob"));
		}, "image/png");
	});
}

/** Draw the 11-slot evolution progress bar. */
function drawProgressBar(ctx, topLevel) {
	const slots = FRUITS.length;
	const filled = Math.min(Math.max(topLevel + 1, 0), slots);
	const gap = 6;
	const totalW = CARD_W - 140;
	const cellW = (totalW - gap * (slots - 1)) / slots;
	const startX = 70;
	const y = 560;

	for (let i = 0; i < slots; i++) {
		ctx.fillStyle = i < filled ? "#43a047" : "#e0e0e0";
		roundRect(ctx, startX + i * (cellW + gap), y, cellW, 16, 4);
		ctx.fill();
	}
}

/** Path a rounded rectangle (no fill/stroke - caller decides). */
function roundRect(ctx, x, y, w, h, radius) {
	const r = Math.min(radius, w / 2, h / 2);
	ctx.beginPath();
	ctx.moveTo(x + r, y);
	ctx.arcTo(x + w, y, x + w, y + h, r);
	ctx.arcTo(x + w, y + h, x, y + h, r);
	ctx.arcTo(x, y + h, x, y, r);
	ctx.arcTo(x, y, x + w, y, r);
	ctx.closePath();
}
