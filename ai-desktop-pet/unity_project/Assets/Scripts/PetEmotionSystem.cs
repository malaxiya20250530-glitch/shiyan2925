using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// 宠物情绪系统 —— 管理情绪值、衰减、触发动画映射。
/// 哪吒·魔童版：新增 fired_up 战鬪状态 + battle_pose 动画。
/// 挂载到 PetCore 所在的 GameObject。
/// </summary>
public class PetEmotionSystem : MonoBehaviour
{
    [Header("情绪衰减设置")]
    public float decayRate = 0.04f;
    public float decayInterval = 5f;

    // 情绪值 [0, 1]
    private Dictionary<string, float> _emotions = new Dictionary<string, float>();
    private float _decayTimer;

    // 情绪→动画映射（哪吒专属版）
    private static readonly Dictionary<string, string> EmotionToAnimation = new Dictionary<string, string>
    {
        { "neutral", "idle" },
        { "happy", "bounce" },
        { "sad", "droop" },
        { "angry", "stomp" },
        { "surprised", "jump" },
        { "excited", "spin" },
        { "sleepy", "yawn" },
        { "shy", "hide" },
        { "fired_up", "battle_pose" }  // 哪吒专属：战鬪姿态，火焰燃起
    };

    // 情绪→表情混合形状 (需在模型中设置 BlendShapes)
    private static readonly Dictionary<string, int> EmotionToBlendShape = new Dictionary<string, int>
    {
        { "happy", 0 },
        { "sad", 1 },
        { "angry", 2 },
        { "surprised", 3 },
        { "sleepy", 4 },
        { "fired_up", 5 }  // 哪吒专属：邪笑 + 火焰瞳孔
    };

    public string DominantEmotion { get; private set; } = "neutral";
    public SkinnedMeshRenderer faceRenderer; // 用于表情混合形状

    void Start()
    {
        // 初始化情绪值
        _emotions["neutral"] = 1.0f;
        _emotions["happy"] = 0.0f;
        _emotions["sad"] = 0.0f;
        _emotions["angry"] = 0.0f;
        _emotions["surprised"] = 0.0f;
        _emotions["excited"] = 0.0f;
        _emotions["sleepy"] = 0.0f;
        _emotions["shy"] = 0.0f;
        _emotions["fired_up"] = 0.0f;  // 哪吒专属情绪
    }

    void Update()
    {
        // 情绪衰减
        _decayTimer += Time.deltaTime;
        if (_decayTimer >= decayInterval)
        {
            _decayTimer = 0f;
            DecayEmotions();
        }
    }

    /// <summary>触发情绪（增加指定情绪值）</summary>
    public void TriggerEmotion(string emotion, float intensity = 0.3f)
    {
        if (!_emotions.ContainsKey(emotion)) return;

        _emotions[emotion] = Mathf.Min(1f, _emotions[emotion] + intensity);
        _emotions["neutral"] = Mathf.Max(0f, _emotions["neutral"] - intensity * 0.5f);

        // 哪吒联动：fired_up 时连带提升 angry 和 excited
        if (emotion == "fired_up")
        {
            _emotions["angry"] = Mathf.Min(1f, _emotions["angry"] + intensity * 0.6f);
            _emotions["excited"] = Mathf.Min(1f, _emotions["excited"] + intensity * 0.4f);
        }

        UpdateDominant();
        UpdateFaceBlendShapes();
    }

    /// <summary>获取情绪的动画名称</summary>
    public string GetAnimationForEmotion(string emotion)
    {
        return EmotionToAnimation.TryGetValue(emotion, out string anim) ? anim : "idle";
    }

    /// <summary>获取当前主导情绪的动画</summary>
    public string GetCurrentAnimation()
    {
        return GetAnimationForEmotion(DominantEmotion);
    }

    // ─── 内部方法 ───

    void DecayEmotions()
    {
        foreach (var key in new List<string>(_emotions.Keys))
        {
            if (key == "neutral") continue;
            _emotions[key] = Mathf.Max(0f, _emotions[key] - decayRate);
        }
        UpdateDominant();
        UpdateFaceBlendShapes();
    }

    void UpdateDominant()
    {
        float maxVal = -1f;
        string maxEmotion = "neutral";

        foreach (var kvp in _emotions)
        {
            if (kvp.Value > maxVal)
            {
                maxVal = kvp.Value;
                maxEmotion = kvp.Key;
            }
        }

        DominantEmotion = maxEmotion;
    }

    void UpdateFaceBlendShapes()
    {
        if (faceRenderer == null) return;

        // 将所有混合形状归零
        foreach (var kvp in EmotionToBlendShape)
        {
            if (kvp.Value < faceRenderer.sharedMesh.blendShapeCount)
            {
                faceRenderer.SetBlendShapeWeight(kvp.Value, 0f);
            }
        }

        // 设置主导情绪的混合形状权重
        if (EmotionToBlendShape.TryGetValue(DominantEmotion, out int idx))
        {
            if (idx < faceRenderer.sharedMesh.blendShapeCount)
            {
                float weight = _emotions[DominantEmotion] * 100f;
                faceRenderer.SetBlendShapeWeight(idx, weight);
            }
        }

        // 哪吒专属：fired_up 时眼睛变金红色
        // 通过 MaterialPropertyBlock 在运行时切换瞳孔颜色
        if (DominantEmotion == "fired_up" && faceRenderer != null)
        {
            MaterialPropertyBlock mpb = new MaterialPropertyBlock();
            faceRenderer.GetPropertyBlock(mpb);
            mpb.SetColor("_EyeColor", new Color(1f, 0.4f, 0f)); // 金红瞳孔
            faceRenderer.SetPropertyBlock(mpb);
        }
    }
}
