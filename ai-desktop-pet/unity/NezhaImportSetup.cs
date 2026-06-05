using UnityEngine;
using UnityEditor;
using System.Linq;

[InitializeOnLoad]
public class NezhaImportSetup : AssetPostprocessor
{
    private static readonly (string name, Color baseColor, float metallic, float smoothness)[] MatConfig = {
        ("Nezha_Skin",       new Color(0.96f, 0.90f, 0.83f), 0f,   0.4f),
        ("Nezha_Vest",       new Color(0.80f, 0.13f, 0.13f), 0f,   0.3f),
        ("Nezha_Hair",       new Color(0.10f, 0.10f, 0.18f), 0.1f, 0.5f),
        ("Nezha_Pants",      new Color(0.29f, 0.29f, 0.35f), 0f,   0.2f),
        ("Nezha_Accessory",  new Color(0.85f, 0.65f, 0.13f), 0.9f, 0.7f),
        ("Nezha_Sash",       new Color(0.80f, 0.13f, 0.13f), 0f,   0.6f),
        ("Nezha_FireWheel",  new Color(0.00f, 0.80f, 1.00f), 0.2f, 0.9f),
        ("Nezha_Eye",        new Color(0.05f, 0.03f, 0.02f), 0f,   0.9f),
    };

    void OnPreprocessModel()
    {
        if (!assetPath.Contains("nezha_textured")) return;
        ModelImporter importer = (ModelImporter)assetImporter;
        importer.animationType = ModelImporterAnimationType.Humanoid;
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        Debug.Log($"[NezhaImport] {assetPath} -> Humanoid Rig OK");
    }

    void OnPostprocessModel(GameObject root)
    {
        if (!assetPath.Contains("nezha_textured")) return;
        var renderers = root.GetComponentsInChildren<Renderer>();
        foreach (var r in renderers)
        {
            foreach (var mat in r.sharedMaterials)
            {
                if (mat == null) continue;
                var cfg = MatConfig.FirstOrDefault(c => mat.name.StartsWith(c.name));
                if (cfg.name == null) continue;
                mat.SetColor("_BaseColor", cfg.baseColor);
                mat.SetFloat("_Metallic", cfg.metallic);
                mat.SetFloat("_Smoothness", cfg.smoothness);
                if (cfg.name == "Nezha_Sash" || cfg.name == "Nezha_Hair")
                    mat.SetFloat("_Cull", 0f);
                if (cfg.name == "Nezha_FireWheel")
                {
                    mat.SetFloat("_Surface", 1f);
                    Color c = cfg.baseColor; c.a = 0.6f;
                    mat.SetColor("_BaseColor", c);
                }
            }
        }
        if (root.GetComponent<PetCore>() == null) root.AddComponent<PetCore>();
        if (root.GetComponent<PetEmotionSystem>() == null) root.AddComponent<PetEmotionSystem>();
        Debug.Log($"[NezhaImport] PetCore+PetEmotionSystem mounted on {root.name}");
    }

    [MenuItem("GameObject/哪吒/手动配置材质", false, 10)]
    static void ManualSetup()
    {
        var go = Selection.activeGameObject;
        if (go == null) { Debug.LogWarning("先选中哪吒模型"); return; }
        var renderers = go.GetComponentsInChildren<Renderer>();
        foreach (var r in renderers)
            foreach (var mat in r.sharedMaterials)
            {
                if (mat == null) continue;
                var cfg = MatConfig.FirstOrDefault(c => mat.name.StartsWith(c.name));
                if (cfg.name == null) continue;
                mat.SetColor("_BaseColor", cfg.baseColor);
                mat.SetFloat("_Metallic", cfg.metallic);
                mat.SetFloat("_Smoothness", cfg.smoothness);
            }
        Debug.Log($"[NezhaImport] 手动配置OK: {go.name}");
    }
}
