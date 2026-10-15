package vn.forgottenworlds.rp;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.class_310;
import net.minecraft.class_642;
import org.slf4j.LoggerFactory;

/** Restores the native optional consent prompt only when explicitly requested. */
public final class ResourcePackRetryClient implements ClientModInitializer {
    private static final Set<String> COMMANDS = Set.of("rp", "goi", "bangtin pack", "sidebar pack");
    private static Set<String> servers = Set.of("snow.pikamc.vn:25079");
    private static final class Config {
        List<String> servers = List.of("snow.pikamc.vn:25079");
    }

    @Override public void onInitializeClient() {
        Path path = FabricLoader.getInstance().getConfigDir().resolve("forgotten-worlds-rp.json");
        Gson json = new GsonBuilder().setPrettyPrinting().create();
        try {
            if (!Files.exists(path)) {
                Files.createDirectories(path.getParent());
                Files.writeString(path, json.toJson(new Config()) + "\n");
            }
            Config config = json.fromJson(Files.readString(path), Config.class);
            if (config == null || config.servers == null) throw new IllegalArgumentException("Missing server list");
            servers = config.servers.stream().filter(s -> s != null && !s.isBlank())
                .map(s -> s.trim().toLowerCase(Locale.ROOT)).collect(Collectors.toUnmodifiableSet());
        } catch (Exception e) {
            LoggerFactory.getLogger("ForgottenResourcePackRetry").warn("Cannot read resource-pack retry server list; using the default server", e);
        }
    }

    public static void requestConsentAgain(String command) {
        if (!COMMANDS.contains(command.trim().toLowerCase(Locale.ROOT))) return;
        class_642 server = class_310.method_1551().method_1558();
        if (server == null || !servers.contains(server.field_3761.trim().toLowerCase(Locale.ROOT))) return;
        // Do not accept/download, clear installed packs, or save settings here.
        // Vanilla opens its normal optional Yes/No screen for the next offer;
        // that screen alone records the player's new decision.
        server.method_2995(class_642.class_643.field_3767);
    }
}
