package com.nostalgia.nosclient;

import com.nostalgia.nosclient.hud.CoordsHud;
import com.nostalgia.nosclient.hud.DayHud;
import com.nostalgia.nosclient.hud.DirectionHud;
import com.nostalgia.nosclient.hud.FpsHud;
import com.nostalgia.nosclient.hud.PingCpsHud;
import com.nostalgia.nosclient.screen.NosClientScreen;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.util.InputUtil;
import org.lwjgl.glfw.GLFW;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class NosClientMod implements ClientModInitializer {

    public static final String MOD_ID = "nos-client";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static KeyBinding openHubKey;
    private static NosClientConfig config;
    private static DragModeHandler dragHandler;

    // HUD instances
    private static CoordsHud coordsHud;
    private static FpsHud fpsHud;
    private static PingCpsHud pingCpsHud;
    private static DirectionHud directionHud;
    private static DayHud dayHud;

    @Override
    public void onInitializeClient() {
        LOGGER.info("[Nos Client] Initializing...");

        config = NosClientConfig.load();
        dragHandler = new DragModeHandler(config);

        coordsHud = new CoordsHud(config);
        fpsHud = new FpsHud(config);
        pingCpsHud = new PingCpsHud(config);
        directionHud = new DirectionHud(config);
        dayHud = new DayHud(config);

        openHubKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.nos-client.open_hub",
                InputUtil.Type.KEYSYM,
                GLFW.GLFW_KEY_RIGHT_SHIFT,
                "category.nos-client"
        ));

        // Register HUD rendering
        HudRenderCallback.EVENT.register((drawContext, tickDelta) -> {
            if (!config.isEnabled()) return;
            MinecraftClient client = MinecraftClient.getInstance();
            if (client.player == null || client.world == null) return;
            if (dragHandler.isDragMode()) return; // Don't render normal HUD in drag mode

            int screenW = client.getWindow().getScaledWidth();
            int screenH = client.getWindow().getScaledHeight();

            if (config.isHudEnabled("coords")) {
                coordsHud.render(drawContext, screenW, screenH);
            }
            if (config.isHudEnabled("fps")) {
                fpsHud.render(drawContext, screenW, screenH);
            }
            if (config.isHudEnabled("ping_cps")) {
                pingCpsHud.render(drawContext, screenW, screenH);
            }
            if (config.isHudEnabled("direction")) {
                directionHud.render(drawContext, screenW, screenH);
            }
            if (config.isHudEnabled("day")) {
                dayHud.render(drawContext, screenW, screenH);
            }
        });

        // Register tick events
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            // Handle key press
            while (openHubKey.wasPressed()) {
                if (client.currentScreen instanceof NosClientScreen) {
                    client.setScreen(null);
                } else if (client.currentScreen == null) {
                    client.setScreen(new NosClientScreen(config, dragHandler));
                }
            }

            // Update CPS counter
            if (client.player != null) {
                pingCpsHud.tick();
                dayHud.tick();
            }
        });

        LOGGER.info("[Nos Client] Initialized successfully.");
    }

    public static NosClientConfig getConfig() {
        return config;
    }

    public static DragModeHandler getDragHandler() {
        return dragHandler;
    }
}
