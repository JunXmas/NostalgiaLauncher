package com.nostalgia.nosclient.screen;

import com.nostalgia.nosclient.DragModeHandler;
import com.nostalgia.nosclient.NosClientConfig;
import com.nostalgia.nosclient.StyleConstants;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.text.Text;

import java.util.ArrayList;
import java.util.List;

public class NosClientScreen extends Screen {

    private final NosClientConfig config;
    private final DragModeHandler dragHandler;
    private final List<ModCard> modCards = new ArrayList<>();
    private int panelX, panelY, panelW, panelH;
    private int scrollOffset = 0;

    // Buttons
    private int dragBtnX, dragBtnY, dragBtnW, dragBtnH;
    private int resetBtnX, resetBtnY, resetBtnW, resetBtnH;

    public NosClientScreen(NosClientConfig config, DragModeHandler dragHandler) {
        super(Text.literal("NOS CLIENT"));
        this.config = config;
        this.dragHandler = dragHandler;
    }

    @Override
    protected void init() {
        super.init();
        modCards.clear();

        modCards.add(new ModCard("coords", "§a⊞§r Coordinates",
                "Hiển thị tọa độ XYZ và biome hiện tại"));
        modCards.add(new ModCard("fps", "§e⊙§r FPS Counter",
                "Hiển thị FPS với mã màu theo hiệu suất"));
        modCards.add(new ModCard("ping_cps", "§b⊕§r Ping & CPS",
                "Hiển thị độ trễ mạng và số click/giây"));
        modCards.add(new ModCard("direction", "§d⊗§r Compass",
                "Thanh la bàn 8 hướng ở trên cùng"));
        modCards.add(new ModCard("day", "§6☀§r Day Counter",
                "Đếm số ngày trong game"));
    }

    @Override
    public boolean shouldPause() {
        return false;
    }

    @Override
    public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
        // If in drag mode, render drag overlay instead
        if (dragHandler.isDragMode()) {
            renderDragMode(ctx, mouseX, mouseY);
            return;
        }

        // Darkened background
        ctx.fill(0, 0, this.width, this.height, 0x80000000);

        // Panel dimensions (60% width, centered)
        panelW = (int) (this.width * 0.6);
        panelH = (int) (this.height * 0.75);
        panelX = (this.width - panelW) / 2;
        panelY = (this.height - panelH) / 2;

        // Panel background (dark glass)
        ctx.fill(panelX, panelY, panelX + panelW, panelY + panelH,
                StyleConstants.COLOR_HUB_BG);

        // Panel border
        ctx.fill(panelX, panelY, panelX + panelW, panelY + 1, StyleConstants.COLOR_BORDER);
        ctx.fill(panelX, panelY + panelH - 1, panelX + panelW, panelY + panelH, StyleConstants.COLOR_BORDER);
        ctx.fill(panelX, panelY, panelX + 1, panelY + panelH, StyleConstants.COLOR_BORDER);
        ctx.fill(panelX + panelW - 1, panelY, panelX + panelW, panelY + panelH, StyleConstants.COLOR_BORDER);

        // Shine strip
        ctx.fill(panelX + 1, panelY + 1, panelX + panelW - 1, panelY + 4, StyleConstants.COLOR_SHINE);

        // Header
        MinecraftClient client = MinecraftClient.getInstance();
        String headerText = "NOS CLIENT";
        int headerX = panelX + (panelW - client.textRenderer.getWidth(headerText)) / 2;
        int headerY = panelY + 12;
        ctx.drawTextWithShadow(client.textRenderer, headerText, headerX, headerY,
                StyleConstants.COLOR_ACCENT);

        String subtitleText = "HUD & Mods";
        int subtitleX = panelX + (panelW - client.textRenderer.getWidth(subtitleText)) / 2;
        int subtitleY = headerY + 14;
        ctx.drawTextWithShadow(client.textRenderer, subtitleText, subtitleX, subtitleY,
                StyleConstants.COLOR_TEXT_DIM);

        // Separator line
        int sepY = subtitleY + 14;
        ctx.fill(panelX + 10, sepY, panelX + panelW - 10, sepY + 1, StyleConstants.COLOR_BORDER);

        // Mod cards grid (2 columns)
        int cardStartY = sepY + 8;
        int cardMargin = 6;
        int cardW = (panelW - 30 - cardMargin) / 2; // 10px padding each side + margin between
        int cardH = 40;

        for (int i = 0; i < modCards.size(); i++) {
            ModCard card = modCards.get(i);
            int col = i % 2;
            int row = i / 2;
            int cardX = panelX + 10 + col * (cardW + cardMargin);
            int cardY = cardStartY + row * (cardH + cardMargin) - scrollOffset;

            if (cardY + cardH < panelY || cardY > panelY + panelH) continue;

            boolean isEnabled = config.isHudEnabled(card.id);
            renderModCard(ctx, cardX, cardY, cardW, cardH, card, isEnabled, mouseX, mouseY);
        }

        // Action buttons at bottom
        int btnY = panelY + panelH - 30;
        int btnH = 20;

        // "Di chuyển HUD" button
        String dragText = "✥ Di chuyển HUD";
        dragBtnW = client.textRenderer.getWidth(dragText) + 16;
        dragBtnX = panelX + panelW / 2 - dragBtnW - 4;
        dragBtnY = btnY;
        dragBtnH = btnH;

        boolean hoverDrag = mouseX >= dragBtnX && mouseX <= dragBtnX + dragBtnW &&
                mouseY >= dragBtnY && mouseY <= dragBtnY + dragBtnH;
        ctx.fill(dragBtnX, dragBtnY, dragBtnX + dragBtnW, dragBtnY + dragBtnH,
                hoverDrag ? 0x40FFFFFF : StyleConstants.COLOR_BG_GLASS);
        ctx.fill(dragBtnX, dragBtnY, dragBtnX + dragBtnW, dragBtnY + 1, StyleConstants.COLOR_BORDER);
        ctx.fill(dragBtnX, dragBtnY + dragBtnH - 1, dragBtnX + dragBtnW, dragBtnY + dragBtnH, StyleConstants.COLOR_BORDER);
        ctx.fill(dragBtnX, dragBtnY, dragBtnX + 1, dragBtnY + dragBtnH, StyleConstants.COLOR_BORDER);
        ctx.fill(dragBtnX + dragBtnW - 1, dragBtnY, dragBtnX + dragBtnW, dragBtnY + dragBtnH, StyleConstants.COLOR_BORDER);
        ctx.drawTextWithShadow(client.textRenderer, dragText,
                dragBtnX + 8, dragBtnY + (dragBtnH - client.textRenderer.fontHeight) / 2,
                StyleConstants.COLOR_ACCENT);

        // "Reset vị trí" button
        String resetText = "↺ Reset vị trí";
        resetBtnW = client.textRenderer.getWidth(resetText) + 16;
        resetBtnX = panelX + panelW / 2 + 4;
        resetBtnY = btnY;
        resetBtnH = btnH;

        boolean hoverReset = mouseX >= resetBtnX && mouseX <= resetBtnX + resetBtnW &&
                mouseY >= resetBtnY && mouseY <= resetBtnY + resetBtnH;
        ctx.fill(resetBtnX, resetBtnY, resetBtnX + resetBtnW, resetBtnY + resetBtnH,
                hoverReset ? 0x40FFFFFF : StyleConstants.COLOR_BG_GLASS);
        ctx.fill(resetBtnX, resetBtnY, resetBtnX + resetBtnW, resetBtnY + 1, StyleConstants.COLOR_BORDER);
        ctx.fill(resetBtnX, resetBtnY + resetBtnH - 1, resetBtnX + resetBtnW, resetBtnY + resetBtnH, StyleConstants.COLOR_BORDER);
        ctx.fill(resetBtnX, resetBtnY, resetBtnX + 1, resetBtnY + resetBtnH, StyleConstants.COLOR_BORDER);
        ctx.fill(resetBtnX + resetBtnW - 1, resetBtnY, resetBtnX + resetBtnW, resetBtnY + resetBtnH, StyleConstants.COLOR_BORDER);
        ctx.drawTextWithShadow(client.textRenderer, resetText,
                resetBtnX + 8, resetBtnY + (resetBtnH - client.textRenderer.fontHeight) / 2,
                StyleConstants.COLOR_TEXT_DIM);
    }

    private void renderModCard(DrawContext ctx, int x, int y, int w, int h,
                               ModCard card, boolean enabled, int mouseX, int mouseY) {
        MinecraftClient client = MinecraftClient.getInstance();

        // Card background
        boolean hover = mouseX >= x && mouseX <= x + w && mouseY >= y && mouseY <= y + h;
        ctx.fill(x, y, x + w, y + h, hover ? 0x40FFFFFF : 0x30FFFFFF);

        // Card border
        ctx.fill(x, y, x + w, y + 1, StyleConstants.COLOR_BORDER);
        ctx.fill(x, y + h - 1, x + w, y + h, StyleConstants.COLOR_BORDER);
        ctx.fill(x, y, x + 1, y + h, StyleConstants.COLOR_BORDER);
        ctx.fill(x + w - 1, y, x + w, y + h, StyleConstants.COLOR_BORDER);

        // Name
        ctx.drawTextWithShadow(client.textRenderer, card.displayName, x + 6, y + 5,
                StyleConstants.COLOR_TEXT);

        // Description
        ctx.drawTextWithShadow(client.textRenderer, card.description, x + 6, y + 18,
                StyleConstants.COLOR_TEXT_DIM);

        // Toggle switch
        int toggleW = 20;
        int toggleH = 10;
        int toggleX = x + w - toggleW - 6;
        int toggleY = y + (h - toggleH) / 2;

        // Track
        ctx.fill(toggleX, toggleY, toggleX + toggleW, toggleY + toggleH,
                enabled ? 0xFF2D8B57 : 0xFF555555);
        // Knob
        int knobX = enabled ? toggleX + toggleW - toggleH : toggleX;
        ctx.fill(knobX, toggleY, knobX + toggleH, toggleY + toggleH,
                enabled ? StyleConstants.COLOR_ACCENT : 0xFFAAAAAA);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if (button != 0) return super.mouseClicked(mouseX, mouseY, button);

        if (dragHandler.isDragMode()) {
            return dragHandler.mouseClicked(mouseX, mouseY);
        }

        // Check drag button
        if (mouseX >= dragBtnX && mouseX <= dragBtnX + dragBtnW &&
                mouseY >= dragBtnY && mouseY <= dragBtnY + dragBtnH) {
            dragHandler.setDragMode(true);
            return true;
        }

        // Check reset button
        if (mouseX >= resetBtnX && mouseX <= resetBtnX + resetBtnW &&
                mouseY >= resetBtnY && mouseY <= resetBtnY + resetBtnH) {
            config.resetPositions();
            config.save();
            return true;
        }

        // Check mod card toggles
        int sepY = panelY + 12 + 14 + 14; // header + subtitle + separator
        int cardStartY = sepY + 8;
        int cardMargin = 6;
        int cardW = (panelW - 30 - cardMargin) / 2;
        int cardH = 40;

        for (int i = 0; i < modCards.size(); i++) {
            ModCard card = modCards.get(i);
            int col = i % 2;
            int row = i / 2;
            int cardX = panelX + 10 + col * (cardW + cardMargin);
            int cardY = cardStartY + row * (cardH + cardMargin) - scrollOffset;

            if (mouseX >= cardX && mouseX <= cardX + cardW &&
                    mouseY >= cardY && mouseY <= cardY + cardH) {
                config.toggleHud(card.id);
                config.save();
                return true;
            }
        }

        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean mouseDragged(double mouseX, double mouseY, int button,
                                double deltaX, double deltaY) {
        if (dragHandler.isDragMode()) {
            return dragHandler.mouseDragged(mouseX, mouseY, this.width, this.height);
        }
        return super.mouseDragged(mouseX, mouseY, button, deltaX, deltaY);
    }

    @Override
    public boolean mouseReleased(double mouseX, double mouseY, int button) {
        if (dragHandler.isDragMode()) {
            return dragHandler.mouseReleased();
        }
        return super.mouseReleased(mouseX, mouseY, button);
    }

    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        // Exit drag mode on Escape
        if (dragHandler.isDragMode()) {
            if (keyCode == 256) { // GLFW_KEY_ESCAPE
                dragHandler.setDragMode(false);
                config.save();
                return true;
            }
            return true; // Consume all keys in drag mode
        }
        return super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY,
                                 double horizontalAmount, double verticalAmount) {
        scrollOffset -= (int) (verticalAmount * 10);
        scrollOffset = Math.max(0, scrollOffset);
        return true;
    }

    private void renderDragMode(DrawContext ctx, int mouseX, int mouseY) {
        // Semi-transparent overlay
        ctx.fill(0, 0, this.width, this.height, 0x40000000);

        // Instruction text at top
        MinecraftClient client = MinecraftClient.getInstance();
        String instructions = "Drag HUD elements to reposition — Press ESC to save & exit";
        int textW = client.textRenderer.getWidth(instructions);
        ctx.drawTextWithShadow(client.textRenderer, instructions,
                (this.width - textW) / 2, 10, StyleConstants.COLOR_ACCENT);

        // Render draggable badges
        dragHandler.tick();
        dragHandler.render(ctx, this.width, this.height);
    }

    private static class ModCard {
        final String id;
        final String displayName;
        final String description;

        ModCard(String id, String displayName, String description) {
            this.id = id;
            this.displayName = displayName;
            this.description = description;
        }
    }
}
