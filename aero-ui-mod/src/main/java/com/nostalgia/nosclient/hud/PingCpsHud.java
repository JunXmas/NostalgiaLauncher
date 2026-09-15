package com.nostalgia.nosclient.hud;

import com.nostalgia.nosclient.NosClientConfig;
import com.nostalgia.nosclient.StyleConstants;
import com.nostalgia.nosclient.render.GlassRenderer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.network.PlayerListEntry;

import java.util.LinkedList;
import java.util.Queue;

public class PingCpsHud {

    private final NosClientConfig config;
    private final Queue<Long> clickTimestamps = new LinkedList<>();
    private int currentCps = 0;

    public PingCpsHud(NosClientConfig config) {
        this.config = config;
    }

    public void registerClick() {
        clickTimestamps.add(System.currentTimeMillis());
    }

    public void tick() {
        long now = System.currentTimeMillis();
        // Remove clicks older than 1 second
        while (!clickTimestamps.isEmpty() && now - clickTimestamps.peek() > 1000) {
            clickTimestamps.poll();
        }
        currentCps = clickTimestamps.size();
    }

    public void render(DrawContext ctx, int screenW, int screenH) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) return;

        int ping = 0;
        if (client.getNetworkHandler() != null) {
            PlayerListEntry entry = client.getNetworkHandler()
                    .getPlayerListEntry(client.player.getUuid());
            if (entry != null) {
                ping = entry.getLatency();
            }
        }

        String text = String.format("Ping: %dms  CPS: %d", ping, currentCps);

        NosClientConfig.HudPosition hudPos = config.getHudPosition("ping_cps");
        int x = (int) (hudPos.xPct * screenW);
        int y = (int) (hudPos.yPct * screenH);
        int w = GlassRenderer.pillWidth(text);
        int h = GlassRenderer.pillHeight();

        x = Math.max(0, Math.min(x, screenW - w));
        y = Math.max(0, Math.min(y, screenH - h));

        GlassRenderer.drawPill(ctx, x, y, w, h, text, StyleConstants.COLOR_TEXT);
    }
}
