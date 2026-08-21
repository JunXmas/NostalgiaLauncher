package com.nostalgia.aeroforge;

import java.util.List;

import net.minecraft.client.Minecraft;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;

/**
 * Khoá cứng resource pack Aero UI trên Forge 1.12.2.
 *
 * <p>Forge 1.12.2 KHÔNG có API kiểu Fabric {@code ALWAYS_ENABLED}. Cách khoá: mỗi
 * ~2 giây kiểm tra danh sách resource pack đang bật; nếu pack "Aero UI.zip" bị gỡ
 * hoặc không ở cuối (ưu tiên cao nhất) thì thêm lại + nạp lại tài nguyên. Người
 * chơi có tắt trong menu thì lần tick sau nó tự bật lại -> coi như không tắt được.
 *
 * <p>Pack "Aero UI.zip" do launcher đặt sẵn trong {@code resourcepacks/} (soft-lock
 * cho bản legacy). Mod này lo phần "ép luôn bật + top".
 */
@Mod(modid = AeroForge.MODID, name = "Aero UI", version = "1.0.0",
     clientSideOnly = true, acceptedMinecraftVersions = "[1.12.2]")
public class AeroForge {
    public static final String MODID = "aeroui";
    private static final String PACK = "Aero UI.zip";
    private int cooldown;

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(this);
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) {
            return;
        }
        if (cooldown > 0) {
            cooldown--;
            return;
        }
        cooldown = 40; // ~2s (20 tick/giây) — đủ nhạy mà không tốn.

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.gameSettings == null) {
            return;
        }
        List<String> packs = mc.gameSettings.resourcePacks;
        boolean top = !packs.isEmpty() && PACK.equals(packs.get(packs.size() - 1));
        if (top) {
            return; // đã bật + ở cuối = ưu tiên cao nhất -> khỏi làm gì.
        }
        // Bị tắt/không ở top -> ép về cuối rồi nạp lại (chỉ chạy khi có thay đổi).
        packs.remove(PACK);
        packs.add(PACK);
        mc.gameSettings.saveOptions();
        mc.refreshResources();
    }
}
