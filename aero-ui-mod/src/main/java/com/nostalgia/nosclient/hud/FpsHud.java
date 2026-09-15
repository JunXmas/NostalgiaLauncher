package com.nostalgia.nosclient.hud;

import com.nostalgia.nosclient.NosClientConfig;
import com.nostalgia.nosclient.StyleConstants;
import com.nostalgia.nosclient.render.GlassRenderer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;

public class FpsHud {

    private final NosClientConfig config;

    public FpsHud(NosClientConfig config) {
        this.config = config;
    }

    public void render(DrawContext ctx, int screenW, int screenH) {
        MinecraftClient client = MinecraftClient.getInstance();
        int fps = client.getCurrentFps();

        String text = "FPS: " + fps;

        int color;
        if (fps > 60) {
            color = StyleConstants.COLOR_FPS_GOOD;
        } else if (fps >= 30) {
            color = StyleConstants.COLOR_FPS_MEDIUM;
        } else {
            color = StyleConstants.COLOR_FPS_BAD;
        }

        NosClientConfig.HudPosition hudPos = config.getHudPosition("fps");
        int x = (int) (hudPos.xPct * screenW);
        int y = (int) (hudPos.yPct * screenH);
        int w = GlassRenderer.pillWidth(text);
        int h = GlassRenderer.pillHeight();

        x = Math.max(0, Math.min(x, screenW - w));
        y = Math.max(0, Math.min(y, screenH - h));

        GlassRenderer.drawPill(ctx, x, y, w, h, text, color);
    }
}
