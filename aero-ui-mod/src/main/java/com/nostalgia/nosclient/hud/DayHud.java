package com.nostalgia.nosclient.hud;

import com.nostalgia.nosclient.NosClientConfig;
import com.nostalgia.nosclient.StyleConstants;
import com.nostalgia.nosclient.render.GlassRenderer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;

public class DayHud {

    private final NosClientConfig config;
    private int tickCounter = 0;
    private long cachedDay = 0;

    public DayHud(NosClientConfig config) {
        this.config = config;
    }

    public void tick() {
        tickCounter++;
        if (tickCounter >= 40) { // Refresh every 2 seconds (40 ticks)
            tickCounter = 0;
            MinecraftClient client = MinecraftClient.getInstance();
            if (client.world != null) {
                cachedDay = client.world.getTimeOfDay() / 24000L;
            }
        }
    }

    public void render(DrawContext ctx, int screenW, int screenH) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.world == null) return;

        // Use cached value, but update on first render
        if (cachedDay == 0 && client.world != null) {
            cachedDay = client.world.getTimeOfDay() / 24000L;
        }

        String text = "Ngày: " + cachedDay;

        NosClientConfig.HudPosition hudPos = config.getHudPosition("day");
        int w = GlassRenderer.pillWidth(text);
        int h = GlassRenderer.pillHeight();
        // Right-align for day HUD (xPct near 1.0)
        int x = (int) (hudPos.xPct * screenW) - w;
        int y = (int) (hudPos.yPct * screenH);

        x = Math.max(0, Math.min(x, screenW - w));
        y = Math.max(0, Math.min(y, screenH - h));

        GlassRenderer.drawPill(ctx, x, y, w, h, text, StyleConstants.COLOR_TEXT);
    }
}
