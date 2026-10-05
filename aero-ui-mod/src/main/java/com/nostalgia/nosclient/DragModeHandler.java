package com.nostalgia.nosclient;

import com.nostalgia.nosclient.render.GlassRenderer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;

import java.util.LinkedHashMap;
import java.util.Map;

public class DragModeHandler {

    private final NosClientConfig config;
    private boolean dragMode = false;
    private String draggingHud = null;
    private int dragOffsetX = 0;
    private int dragOffsetY = 0;
    private long animationTick = 0;

    // Cached badge dimensions for hit-testing
    private final Map<String, int[]> badgeBounds = new LinkedHashMap<>();

    public DragModeHandler(NosClientConfig config) {
        this.config = config;
    }

    public boolean isDragMode() {
        return dragMode;
    }

    public void setDragMode(boolean dragMode) {
        this.dragMode = dragMode;
        this.draggingHud = null;
        if (dragMode) {
            animationTick = 0;
        }
    }

    public void toggleDragMode() {
        setDragMode(!dragMode);
    }

    public void tick() {
        if (dragMode) {
            animationTick++;
        }
    }

    public void render(DrawContext drawContext, int screenW, int screenH) {
        if (!dragMode) return;

        // Calculate border alpha using sine wave for blink effect
        float sinVal = (float) Math.sin(animationTick * 0.15);
        int blinkAlpha = (int) (128 + 127 * sinVal);
        int borderColor = (blinkAlpha << 24) | (0x4ADE80); // green with animated alpha

        // Render each HUD badge placeholder with blinking border
        String[] hudNames = {"coords", "fps", "ping_cps", "direction", "day"};
        String[] hudLabels = {"Coords (XYZ)", "FPS", "Ping / CPS", "Direction", "Day"};

        badgeBounds.clear();
        MinecraftClient client = MinecraftClient.getInstance();

        for (int i = 0; i < hudNames.length; i++) {
            String name = hudNames[i];
            NosClientConfig.HudPosition pos = config.getHudPosition(name);
            int textWidth = client.textRenderer.getWidth(hudLabels[i]);
            int w = textWidth + StyleConstants.PILL_PAD_X * 2;
            int h = client.textRenderer.fontHeight + StyleConstants.PILL_PAD_Y * 2;

            int x = (int) (pos.xPct * screenW);
            int y = (int) (pos.yPct * screenH);

            // Clamp
            x = Math.max(0, Math.min(x, screenW - w));
            y = Math.max(0, Math.min(y, screenH - h));

            // Draw glass pill
            GlassRenderer.drawPill(drawContext, x, y, w, h, hudLabels[i], StyleConstants.COLOR_TEXT);

            // Draw blinking green border
            drawContext.fill(x, y, x + w, y + 1, borderColor);           // top
            drawContext.fill(x, y + h - 1, x + w, y + h, borderColor);   // bottom
            drawContext.fill(x, y, x + 1, y + h, borderColor);           // left
            drawContext.fill(x + w - 1, y, x + w, y + h, borderColor);   // right

            badgeBounds.put(name, new int[]{x, y, w, h});
        }
    }

    public boolean mouseClicked(double mouseX, double mouseY) {
        if (!dragMode) return false;

        for (Map.Entry<String, int[]> entry : badgeBounds.entrySet()) {
            int[] b = entry.getValue();
            if (mouseX >= b[0] && mouseX <= b[0] + b[2] &&
                    mouseY >= b[1] && mouseY <= b[1] + b[3]) {
                draggingHud = entry.getKey();
                dragOffsetX = (int) mouseX - b[0];
                dragOffsetY = (int) mouseY - b[1];
                return true;
            }
        }
        return false;
    }

    public boolean mouseDragged(double mouseX, double mouseY, int screenW, int screenH) {
        if (!dragMode || draggingHud == null) return false;

        int[] b = badgeBounds.get(draggingHud);
        if (b == null) return false;

        int newX = (int) mouseX - dragOffsetX;
        int newY = (int) mouseY - dragOffsetY;

        // Snap to 4px grid
        newX = (newX / 4) * 4;
        newY = (newY / 4) * 4;

        // Clamp within screen
        newX = Math.max(0, Math.min(newX, screenW - b[2]));
        newY = Math.max(0, Math.min(newY, screenH - b[3]));

        // Convert to percentage
        float xPct = screenW > 0 ? (float) newX / screenW : 0f;
        float yPct = screenH > 0 ? (float) newY / screenH : 0f;

        config.setHudPosition(draggingHud, xPct, yPct);
        return true;
    }

    public boolean mouseReleased() {
        if (!dragMode || draggingHud == null) return false;
        draggingHud = null;
        config.save();
        return true;
    }
}
