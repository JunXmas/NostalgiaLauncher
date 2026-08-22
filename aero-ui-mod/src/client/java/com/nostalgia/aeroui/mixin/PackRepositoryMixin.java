package com.nostalgia.aeroui.mixin;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.repository.PackRepository;

/**
 * Khoá cứng "top priority" cho resource pack Aero UI.
 *
 * <p>{@code ALWAYS_ENABLED} (xem {@code AeroUiClient}) đã đảm bảo pack luôn BẬT và
 * người chơi không tắt được — nhưng nó KHÔNG chặn việc một pack khác xếp trên đè
 * texture của mình. Mixin này bịt nốt kẽ hở đó: mỗi lần {@code PackRepository} dựng
 * lại danh sách pack đang bật ({@code rebuildSelected}), ta đẩy pack Aero UI xuống
 * CUỐI danh sách.
 *
 * <p>Trong Minecraft, danh sách {@code selected} được áp theo thứ tự "sau đè trước"
 * (phần tử cuối = ưu tiên cao nhất, thắng mọi override). Đưa pack của mình về cuối
 * nên nó luôn thắng — kể cả pack người chơi tự thêm hay pack có {@code Position.TOP}
 * khác. Thao tác idempotent: chạy lại vẫn cho đúng một kết quả, nên an toàn khi
 * người chơi cố kéo/đổi thứ tự trong menu Resource Packs.
 *
 * <p>Chỉ nhắm dòng 1.21.x (khớp dải {@code minecraft: ">=1.21"} của mod). Tên
 * {@code rebuildSelected}/{@code Pack.getId} ổn định trong dòng này; đổi major
 * (1.20 trở về trước) có thể phải chỉnh target — xem README.
 */
@Mixin(PackRepository.class)
public class PackRepositoryMixin {

	@Inject(method = "rebuildSelected", at = @At("RETURN"), cancellable = true)
	private void aeroui$forceTopPriority(Collection<String> ids,
			CallbackInfoReturnable<List<Pack>> cir) {
		List<Pack> selected = cir.getReturnValue();
		// < 2 pack thì không có gì để sắp; null phòng thân trước mọi bất ngờ.
		if (selected == null || selected.size() < 2) {
			return;
		}

		Pack ours = null;
		for (Pack pack : selected) {
			// Khớp lỏng theo id để bền với mọi tiền tố mà Fabric gán cho builtin
			// pack (vd "aero-ui/aero-ui", "aero-ui:aero-ui"...).
			if (pack.getId().contains("aero-ui")) {
				ours = pack;
				break;
			}
		}
		// Không thấy pack (ALWAYS_ENABLED lo phần BẬT, không phải việc của Mixin
		// này), hoặc đã ở cuối rồi -> khỏi động vào.
		if (ours == null || selected.get(selected.size() - 1) == ours) {
			return;
		}

		List<Pack> reordered = new ArrayList<>(selected);
		reordered.remove(ours);
		reordered.add(ours); // cuối danh sách = áp sau cùng = ưu tiên cao nhất
		// Collections.unmodifiableList thay cho List.copyOf (Java 10) để build được
		// cả release 8 (1.16.5). Ngữ nghĩa như nhau: trả danh sách bất biến.
		cir.setReturnValue(Collections.unmodifiableList(reordered));
	}
}
