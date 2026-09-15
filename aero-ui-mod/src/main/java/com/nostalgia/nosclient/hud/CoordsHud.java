package com.nostalgia.nosclient.hud;

import com.nostalgia.nosclient.NosClientConfig;
import com.nostalgia.nosclient.StyleConstants;
import com.nostalgia.nosclient.render.GlassRenderer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.registry.entry.RegistryEntry;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.biome.Biome;

public class CoordsHud {

    private final NosClientConfig config;

    public CoordsHud(NosClientConfig config) {
        this.config = config;
    }

    public void render(DrawContext ctx, int screenW, int screenH) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null || client.world == null) return;

        BlockPos pos = client.player.getBlockPos();
        RegistryEntry<Biome> biomeEntry = client.world.getBiome(pos);
        String biomeName = biomeEntry.getKey()
                .map(key -> key.getValue().getPath())
                .orElse("unknown");

        String text = String.format("XYZ: %d / %d / %d [%s]",
                pos.getX(), pos.getY(), pos.getZ(), biomeName);

        NosClientConfig.HudPosition hudPos = config.getHudPosition("coords");
        int x = (int) (hudPos.xPct * screenW);
        int y = (int) (hudPos.yPct * screenH);
        int w = GlassRenderer.pillWidth(text);
        int h = GlassRenderer.pillHeight();

        // Clamp
        x = Math.max(0, Math.min(x, screenW - w));
        y = Math.max(0, Math.min(y, screenH - h));

        GlassRenderer.drawPill(ctx, x, y, w, h, text, StyleConstants.COLOR_TEXT);
    }
}
