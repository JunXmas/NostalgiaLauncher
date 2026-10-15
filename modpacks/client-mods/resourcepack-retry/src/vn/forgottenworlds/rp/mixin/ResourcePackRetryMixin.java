package vn.forgottenworlds.rp.mixin;

import net.minecraft.class_634;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import vn.forgottenworlds.rp.ResourcePackRetryClient;

@Mixin(class_634.class)
public abstract class ResourcePackRetryMixin {
    @Inject(method = "method_45730(Ljava/lang/String;)V", at = @At("HEAD"))
    private void forgotten$requestResourcePackConsent(String command, CallbackInfo ci) {
        ResourcePackRetryClient.requestConsentAgain(command);
    }
}
