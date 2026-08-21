package com.nostalgia.aeroui;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.resource.ResourceManagerHelper;
import net.fabricmc.fabric.api.resource.ResourcePackActivationType;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.resources.Identifier;

/**
 * Đăng ký resource pack Aero UI (nhúng trong jar tại resourcepacks/aero-ui) ở chế
 * độ ALWAYS_ENABLED: pack luôn bật và người chơi KHÔNG thể tắt trong menu — đây là
 * cách "khoá cứng" mà một resource pack thường không làm được.
 */
public class AeroUiClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		FabricLoader.getInstance().getModContainer("aero-ui").ifPresent(container ->
			ResourceManagerHelper.registerBuiltinResourcePack(
				Identifier.fromNamespaceAndPath("aero-ui", "aero-ui"),
				container,
				ResourcePackActivationType.ALWAYS_ENABLED));
	}
}
