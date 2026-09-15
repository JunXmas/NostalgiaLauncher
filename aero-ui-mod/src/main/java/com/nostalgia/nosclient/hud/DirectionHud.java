package com.nostalgia.nosclient.hud;

import com.nostalgia.nosclient.NosClientConfig;
import com.nostalgia.nosclient.StyleConstants;
import com.nostalgia.nosclient.render.GlassRenderer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;

public class DirectionHud {

    private static final String[] DIRECTIONS = {"S", "SW", "W", "NW", "N", "NE", "E", "SE"};

    private final NosClientConfig config;

    public DirectionHud(NosClientConfig config) {
        this.config = config;
    }

    public void render(DrawContext ctx, int screenW, int screenH) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) return;

        float yaw = client.player.getYaw() % 360;
        if (yaw < 0) yaw += 360;

        // Calculate direction index (0=S, 1=SW, ... 7=SE)
        int dirIndex = Math.round(yaw / 45f) % 8;

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < DIRECTIONS.length; i++) {
            if (i > 0) sb.append(" ");
            if (i == dirIndex) {
                sb.append("[").append(DIRECTIONS[i]).append("]");
            } else {
                sb.append(DIRECTIONS[i]);
            }
        }
        String text = sb.toString();

        NosClientConfig.HudPosition hudPos = config.getHudPosition("direction");
        int w = GlassRenderer.pillWidth(text);
        int h = GlassRenderer.pillHeight();
        int x = (int) (hudPos.xPct * screenW) - w / 2; // Center horizontally
        int y = (int) (hudPos.yPct * screenH);

        x = Math.max(0, Math.min(x, screenW - w));
        y = Math.max(0, Math.min(y, screenH - h));

        // Draw pill background
        ctx.fill(x, y, x + w, y + h, StyleConstants.COLOR_BG_GLASS);
        // Border
        ctx.fill(x, y, x + w, y + 1, StyleConstants.COLOR_BORDER);
        ctx.fill(x, y + h - 1, x + w, y + h, StyleConstants.COLOR_BORDER);
        ctx.fill(x, y, x + 1, y + h, StyleConstants.COLOR_BORDER);
        ctx.fill(x + w - 1, y, x + w, y + h, StyleConstants.COLOR_BORDER);
        // Shine
        ctx.fill(x + 1, y + 1, x + w - 1, y + 4, StyleConstants.COLOR_SHINE);

        // Render each direction segment with color
        int textX = x + StyleConstants.PILL_PAD_X;
        int textY = y + StyleConstants.PILL_PAD_Y;

        for (int i = 0; i < DIRECTIONS.length; i++) {
            String segment;
            int color;
            if (i == dirIndex) {
                segment = "[" + DIRECTIONS[i] + "]";
                color = StyleConstants.COLOR_ACCENT;
            } else {
                segment = DIRECTIONS[i];
                color = StyleConstants.COLOR_TEXT_DIM;
            }

            ctx.drawTextWithShadow(client.textRenderer, segment, textX, textY, color);
            textX += client.textRenderer.getWidth(segment + " ");
        }
    }
}
