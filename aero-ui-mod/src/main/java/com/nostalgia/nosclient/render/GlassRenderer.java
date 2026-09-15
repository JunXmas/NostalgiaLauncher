package com.nostalgia.nosclient.render;

import com.nostalgia.nosclient.StyleConstants;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;

public final class GlassRenderer {

    private GlassRenderer() {}

    /**
     * Draw a glass pill badge with background, border, shine strip, and text.
     */
    public static void drawPill(DrawContext ctx, int x, int y, int w, int h,
                                String text, int textColor) {
        // 1. Background fill (dark glass)
        ctx.fill(x, y, x + w, y + h, StyleConstants.COLOR_BG_GLASS);

        // 2. Border (subtle white)
        // Top
        ctx.fill(x, y, x + w, y + 1, StyleConstants.COLOR_BORDER);
        // Bottom
        ctx.fill(x, y + h - 1, x + w, y + h, StyleConstants.COLOR_BORDER);
        // Left
        ctx.fill(x, y, x + 1, y + h, StyleConstants.COLOR_BORDER);
        // Right
        ctx.fill(x + w - 1, y, x + w, y + h, StyleConstants.COLOR_BORDER);

        // 3. Shine strip at top
        ctx.fill(x + 1, y + 1, x + w - 1, y + 4, StyleConstants.COLOR_SHINE);

        // 4. Text
        ctx.drawTextWithShadow(
                MinecraftClient.getInstance().textRenderer,
                text,
                x + StyleConstants.PILL_PAD_X,
                y + StyleConstants.PILL_PAD_Y,
                textColor
        );
    }

    /**
     * Calculate the width of a pill for given text.
     */
    public static int pillWidth(String text) {
        return MinecraftClient.getInstance().textRenderer.getWidth(text)
                + StyleConstants.PILL_PAD_X * 2;
    }

    /**
     * Calculate the height of a pill.
     */
    public static int pillHeight() {
        return MinecraftClient.getInstance().textRenderer.fontHeight
                + StyleConstants.PILL_PAD_Y * 2;
    }
}
