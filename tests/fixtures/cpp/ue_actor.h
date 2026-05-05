// Unreal Engine actor + component fixture. Exercises the full UE
// reflection-macro vocabulary the adapter recognises:
// - UCLASS / USTRUCT / UENUM / UINTERFACE on type declarations
// - UPROPERTY / UFUNCTION on members
// - GENERATED_BODY family inside class bodies (silently dropped)
//
// This file does NOT use *_API DLL-export macros (ENGINE_API,
// MYGAME_API, …) — those need preprocessor expansion to parse
// cleanly and aren't required to demonstrate UE-macro recognition.
#pragma once

#include "MyActor.generated.h"

UENUM(BlueprintType)
enum class EWeaponSlot : uint8
{
    Primary,
    Secondary,
    Sidearm
};

USTRUCT(BlueprintType)
struct FItemData
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString Name;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    int32 Count;

    UPROPERTY()
    EWeaponSlot Slot;
};

UINTERFACE(MinimalAPI, Blueprintable)
class UInteractable : public UInterface
{
    GENERATED_BODY()
};

class IInteractable
{
    GENERATED_IINTERFACE_BODY()

public:
    UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category="Interaction")
    void Interact();
};

UCLASS(Blueprintable, BlueprintType)
class AMyActor : public AActor, public IInteractable
{
    GENERATED_BODY()

public:
    AMyActor();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
    float Health;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components")
    UStaticMeshComponent* Mesh;

    UPROPERTY(EditDefaultsOnly, Category="Combat")
    TArray<FItemData> Inventory;

    UFUNCTION(BlueprintCallable, Category="Combat")
    virtual void TakeDamage(float Amount);

    UFUNCTION(BlueprintNativeEvent, Category="Events")
    void OnHit();

    UFUNCTION()
    void HandleOverlap(AActor* Other);

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
};

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class UMyComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UMyComponent();

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float Speed = 600.0f;

    UFUNCTION(BlueprintCallable)
    void Activate(bool bReset);
};
