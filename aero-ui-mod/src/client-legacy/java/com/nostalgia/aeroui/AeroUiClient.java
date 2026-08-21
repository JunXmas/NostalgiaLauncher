package com.nostalgia.aeroui;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.resource.ResourceManagerHelper;
import net.fabricmc.fabric.api.resource.ResourcePackActivationType;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.resources.ResourceLocation;

/**
 * Bản "legacy" (≤ 1.20.x): giống bản modern nhưng lớp id vẫn là
 * {@code ResourceLocation} với constructor {@code (namespace, path)} — 1.21 mới đổi
 * tên thành {@code Identifier}/{@code fromNamespaceAndPath}. Cùng logic ALWAYS_ENABLED.
 */
public class AeroUiClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		FabricLoader.getInstance().getModContainer("aero-ui").ifPresent(container ->
			ResourceManagerHelper.registerBuiltinResourcePack(
				new ResourceLocation("aero-ui", "aero-ui"),
				container,
				ResourcePackActivationType.ALWAYS_ENABLED));
	}
}
