package com.nostalgia.nosclient;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.fabricmc.loader.api.FabricLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

public class NosClientConfig {

    private static final Logger LOGGER = LoggerFactory.getLogger("nos-client-config");
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String CONFIG_FILE = "nos-client.json";

    private boolean enabled = true;
    private Map<String, Boolean> huds = new HashMap<>();
    private Map<String, HudPosition> hudPositions = new HashMap<>();

    public static class HudPosition {
        public float xPct;
        public float yPct;

        public HudPosition() {}

        public HudPosition(float xPct, float yPct) {
            this.xPct = xPct;
            this.yPct = yPct;
        }
    }

    public NosClientConfig() {
        // Set defaults
        huds.put("coords", true);
        huds.put("fps", true);
        huds.put("ping_cps", true);
        huds.put("direction", false);
        huds.put("day", false);

        hudPositions.put("coords", new HudPosition(0.006f, 0.011f));
        hudPositions.put("fps", new HudPosition(0.006f, 0.083f));
        hudPositions.put("ping_cps", new HudPosition(0.006f, 0.119f));
        hudPositions.put("direction", new HudPosition(0.5f, 0.011f));
        hudPositions.put("day", new HudPosition(0.994f, 0.011f));
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isHudEnabled(String hudName) {
        return huds.getOrDefault(hudName, false);
    }

    public void setHudEnabled(String hudName, boolean value) {
        huds.put(hudName, value);
    }

    public void toggleHud(String hudName) {
        huds.put(hudName, !isHudEnabled(hudName));
    }

    public HudPosition getHudPosition(String hudName) {
        return hudPositions.getOrDefault(hudName, new HudPosition(0f, 0f));
    }

    public void setHudPosition(String hudName, float xPct, float yPct) {
        hudPositions.put(hudName, new HudPosition(
                Math.max(0f, Math.min(1f, xPct)),
                Math.max(0f, Math.min(1f, yPct))
        ));
    }

    public void resetPositions() {
        hudPositions.put("coords", new HudPosition(0.006f, 0.011f));
        hudPositions.put("fps", new HudPosition(0.006f, 0.083f));
        hudPositions.put("ping_cps", new HudPosition(0.006f, 0.119f));
        hudPositions.put("direction", new HudPosition(0.5f, 0.011f));
        hudPositions.put("day", new HudPosition(0.994f, 0.011f));
    }

    public Map<String, Boolean> getHuds() {
        return huds;
    }

    public static NosClientConfig load() {
        Path configPath = FabricLoader.getInstance().getConfigDir().resolve(CONFIG_FILE);
        if (Files.exists(configPath)) {
            try (Reader reader = Files.newBufferedReader(configPath)) {
                NosClientConfig loaded = GSON.fromJson(reader, NosClientConfig.class);
                if (loaded != null) {
                    LOGGER.info("[Nos Client] Config loaded from {}", configPath);
                    return loaded;
                }
            } catch (IOException e) {
                LOGGER.error("[Nos Client] Failed to load config, using defaults", e);
            }
        }
        NosClientConfig defaultConfig = new NosClientConfig();
        defaultConfig.save();
        return defaultConfig;
    }

    public void save() {
        Path configPath = FabricLoader.getInstance().getConfigDir().resolve(CONFIG_FILE);
        try {
            Files.createDirectories(configPath.getParent());
            try (Writer writer = Files.newBufferedWriter(configPath)) {
                GSON.toJson(this, writer);
            }
            LOGGER.info("[Nos Client] Config saved to {}", configPath);
        } catch (IOException e) {
            LOGGER.error("[Nos Client] Failed to save config", e);
        }
    }
}
