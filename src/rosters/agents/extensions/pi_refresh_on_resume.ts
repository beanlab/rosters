import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { TUI } from "@earendil-works/pi-tui";

/** Force Pi to repaint its complete TUI whenever myteam requests a redraw. */
export default function (pi: ExtensionAPI) {
	let tui: TUI | undefined;
	let listening = false;

	const redraw = () => {
		tui?.requestRender(true);
	};

	const handleSigwinch = () => {
		redraw();
	};

	const stopListening = () => {
		if (!listening) return;
		process.off("SIGWINCH", handleSigwinch);
		listening = false;
	};

	pi.registerCommand("redraw", {
		description: "Force a complete TUI redraw",
		handler: async () => {
			redraw();
		},
	});

	pi.on("session_start", (_event, ctx) => {
		if (ctx.mode !== "tui") return;

		ctx.ui.setWidget("myteam-force-redraw", (activeTui) => {
			tui = activeTui;
			if (!listening) {
				process.on("SIGWINCH", handleSigwinch);
				listening = true;
			}

			return {
				render: () => [],
				invalidate: () => {},
				dispose: () => {
					if (tui === activeTui) tui = undefined;
					stopListening();
				},
			};
		});
	});

	pi.on("session_shutdown", () => {
		tui = undefined;
		stopListening();
	});
}
