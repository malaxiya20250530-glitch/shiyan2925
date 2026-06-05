using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// 哪吒程序化舞蹈引擎 — 纯代码驱动21根骨骼实时跳舞
/// 零 AnimationClip 依赖，BPM 同步，多种舞风无缝切换
/// </summary>
public class NezhaDancer : MonoBehaviour
{
    [Header("骨骼引用")]
    public Transform hips;
    public Transform spine, spine1, spine2;
    public Transform neck, head;
    public Transform leftShoulder, leftArm, leftForeArm, leftHand;
    public Transform rightShoulder, rightArm, rightForeArm, rightHand;
    public Transform leftUpLeg, leftLeg, leftFoot;
    public Transform rightUpLeg, rightLeg, rightFoot;

    [Header("舞蹈参数")]
    [Range(60, 200)] public float bpm = 120f;
    [Range(0.1f, 3f)] public float energy = 1f; // 活力倍率
    [Range(0, 1)] public float styleBlend;       // 舞风混合 (0=国风, 1=街舞)

    [Header("骨骼幅度")]
    public float hipSway = 8f;
    public float spineWave = 6f;
    public float armSwing = 25f;
    public float legLift = 20f;
    public float headBob = 5f;
    public float shoulderShrug = 10f;

    [Header("fired_up 增强")]
    [Range(1, 5)] public float firedUpMultiplier = 2.5f;
    public bool addBackflip = true;

    // 内部状态
    private float _beatTime;
    private float _beatDuration;
    private int _beatCount;
    private Quaternion[] _boneRestRots;
    private Transform[] _boneOrder;
    private bool _isFiredUp;

    // 舞步序列
    private enum DanceMove { Idle, Bounce, Wave, SpinPrep, Spin, Stomp, ArmWave, Kick, HeadBang }
    private DanceMove _currentMove;
    private float _moveTimer;
    private float _moveDuration;
    private System.Random _rng;

    void Start()
    {
        AutoFindBones();
        CacheRestRotations();
        _beatDuration = 60f / bpm;
        _rng = new System.Random(42);
        PickNextMove();
    }

    void AutoFindBones()
    {
        var all = GetComponentsInChildren<Transform>();
        foreach (var t in all)
        {
            switch (t.name)
            {
                case "Hips": hips = t; break;
                case "Spine": spine = t; break;
                case "Spine1": spine1 = t; break;
                case "Spine2": spine2 = t; break;
                case "Neck": neck = t; break;
                case "Head": head = t; break;
                case "LeftShoulder": leftShoulder = t; break;
                case "LeftArm": leftArm = t; break;
                case "LeftForeArm": leftForeArm = t; break;
                case "LeftHand": leftHand = t; break;
                case "RightShoulder": rightShoulder = t; break;
                case "RightArm": rightArm = t; break;
                case "RightForeArm": rightForeArm = t; break;
                case "RightHand": rightHand = t; break;
                case "LeftUpLeg": leftUpLeg = t; break;
                case "LeftLeg": leftLeg = t; break;
                case "LeftFoot": leftFoot = t; break;
                case "RightUpLeg": rightUpLeg = t; break;
                case "RightLeg": rightLeg = t; break;
                case "RightFoot": rightFoot = t; break;
            }
        }
    }

    void CacheRestRotations()
    {
        _boneOrder = new[] { hips, spine, spine1, spine2, neck, head,
            leftShoulder, leftArm, leftForeArm, leftHand,
            rightShoulder, rightArm, rightForeArm, rightHand,
            leftUpLeg, leftLeg, leftFoot,
            rightUpLeg, rightLeg, rightFoot };
        _boneRestRots = new Quaternion[_boneOrder.Length];
        for (int i = 0; i < _boneOrder.Length; i++)
            if (_boneOrder[i] != null)
                _boneRestRots[i] = _boneOrder[i].localRotation;
    }

    void Update()
    {
        _beatTime += Time.deltaTime * energy;
        float beatDuration = _beatDuration / energy;
        float phase = (_beatTime % beatDuration) / beatDuration; // 0→1 per beat
        float phase2 = phase * 2f; // 0→2 per beat
        float sinB = Mathf.Sin(phase * Mathf.PI * 2);
        float cosB = Mathf.Cos(phase * Mathf.PI * 2);

        if (_beatTime >= beatDuration)
        {
            _beatTime -= beatDuration;
            _beatCount++;
            OnBeat();
        }

        // ── 髋部摇摆（永动） ──
        ApplyRot(hips, Quaternion.Euler(0, sinB * hipSway, 0));

        // ── 脊柱波浪 ──
        float spinePhase = phase * 2;
        float s0 = Mathf.Sin(spinePhase * Mathf.PI) * spineWave;
        float s1 = Mathf.Sin((spinePhase + 0.3f) * Mathf.PI) * spineWave * 0.8f;
        float s2 = Mathf.Sin((spinePhase + 0.6f) * Mathf.PI) * spineWave * 0.5f;
        ApplyRot(spine,  Quaternion.Euler(s0 * 0.5f, 0, 0));
        ApplyRot(spine1, Quaternion.Euler(s1 * 0.3f, 0, 0));
        ApplyRot(spine2, Quaternion.Euler(s2 * 0.2f, sinB * 3f, 0));

        // ── 脖子 + 头 ──
        ApplyRot(neck, Quaternion.Euler(Mathf.Sin(phase * Mathf.PI) * headBob, cosB * 5f, 0));
        ApplyRot(head, Quaternion.Euler(sinB * headBob * 0.5f, 0, cosB * 2f));

        // ── 肩膀 ──
        float shrug = Mathf.Abs(sinB) * shoulderShrug;
        ApplyRot(leftShoulder,  Quaternion.Euler(0, 0, -shrug));
        ApplyRot(rightShoulder, Quaternion.Euler(0, 0, shrug));

        // ── 手臂（国风 vs 街舞） ──
        float armS = armSwing * energy;

        // 国风：大圆弧
        float classicArmL = Mathf.Sin(phase * Mathf.PI) * armS;
        float classicArmR = Mathf.Sin(phase * Mathf.PI + Mathf.PI) * armS;

        // 街舞：锁舞/机械
        float hiphopArmL = (phase < 0.5f ? phase * 2 : 2 - phase * 2) * armS * 1.5f;
        float hiphopArmR = (phase > 0.5f ? (phase - 0.5f) * 2 : 0) * armS * 1.5f;

        float armLVal = Mathf.Lerp(classicArmL, hiphopArmL, styleBlend);
        float armRVal = Mathf.Lerp(classicArmR, hiphopArmR, styleBlend);

        ApplyRot(leftArm,  Quaternion.Euler(armLVal, 0, sinB * 10f));
        ApplyRot(rightArm, Quaternion.Euler(armRVal, 0, -sinB * 10f));
        ApplyRot(leftForeArm,  Quaternion.Euler(Mathf.Abs(sinB) * 15f, 0, 0));
        ApplyRot(rightForeArm, Quaternion.Euler(Mathf.Abs(sinB) * 15f, 0, 0));

        // 手腕旋转（街舞风）
        if (styleBlend > 0.5f)
        {
            float wristSpin = Time.time * 500f * (styleBlend - 0.5f) * 2f;
            ApplyRot(leftHand,  Quaternion.Euler(0, wristSpin, 0));
            ApplyRot(rightHand, Quaternion.Euler(0, -wristSpin, 0));
        }

        // ── 腿 ──
        float legL = sinB * legLift * energy;
        float legR = cosB * legLift * energy;
        ApplyRot(leftUpLeg,  Quaternion.Euler(legL, 0, 0));
        ApplyRot(rightUpLeg, Quaternion.Euler(legR, 0, 0));
        ApplyRot(leftLeg,  Quaternion.Euler(-Mathf.Abs(legL) * 0.3f, 0, 0));
        ApplyRot(rightLeg, Quaternion.Euler(-Mathf.Abs(legR) * 0.3f, 0, 0));

        // ── 舞步状态机 ──
        _moveTimer += Time.deltaTime;
        if (_moveTimer >= _moveDuration)
            PickNextMove();

        ApplyMove(phase);
    }

    void OnBeat()
    {
        // 重拍 → 小跳
        if (hips != null)
        {
            float bounce = 0.02f * energy;
            if (_isFiredUp) bounce *= firedUpMultiplier;
        }
    }

    void PickNextMove()
    {
        _moveTimer = 0f;
        var moves = System.Enum.GetValues(typeof(DanceMove));
        _currentMove = (DanceMove)moves.GetValue(_rng.Next(moves.Length));
        _moveDuration = _beatDuration * (_rng.Next(2, 8)); // 2-8 拍
    }

    void ApplyMove(float phase)
    {
        float m = _isFiredUp ? firedUpMultiplier : 1f;

        switch (_currentMove)
        {
            case DanceMove.Spin:
                float spinAngle = Mathf.Lerp(0, 360, phase) * m;
                ApplyRot(hips, Quaternion.Euler(0, spinAngle, 0));
                break;
            case DanceMove.Stomp:
                float stomp = (phase < 0.3f ? phase / 0.3f : 0) * legLift * 2 * m;
                ApplyRot(leftUpLeg,  Quaternion.Euler(stomp, 0, 0));
                ApplyRot(rightUpLeg, Quaternion.Euler(stomp, 0, 0));
                break;
            case DanceMove.Kick:
                float kick = Mathf.Sin(phase * Mathf.PI) * 45f * m;
                ApplyRot(rightUpLeg, Quaternion.Euler(kick, 0, 0));
                break;
            case DanceMove.HeadBang:
                float bang = Mathf.Sin(phase * Mathf.PI * 4) * 15f * m;
                ApplyRot(head, Quaternion.Euler(bang, 0, 0));
                break;
            case DanceMove.ArmWave:
                float wave = Mathf.Sin(phase * Mathf.PI * 3) * armSwing * 1.5f * m;
                ApplyRot(leftArm,  Quaternion.Euler(wave, 0, 0));
                ApplyRot(rightArm, Quaternion.Euler(-wave, 0, 0));
                break;
        }

        // fired_up 后空翻
        if (_isFiredUp && addBackflip && _currentMove == DanceMove.Spin)
        {
            float flip = Mathf.Sin(phase * Mathf.PI * 2) * 30f * m;
            ApplyRot(spine, Quaternion.Euler(flip, 0, 0));
        }
    }

    void ApplyRot(Transform bone, Quaternion rot)
    {
        if (bone == null) return;
        int idx = System.Array.IndexOf(_boneOrder, bone);
        if (idx >= 0) bone.localRotation = _boneRestRots[idx] * rot;
    }

    /// <summary>切换 fired_up 狂暴舞姿</summary>
    public void SetFiredUp(bool active)
    {
        _isFiredUp = active;
        energy = active ? 2f : 1f;
        styleBlend = active ? 1f : 0.3f; // fired_up → 街舞风
    }

    /// <summary>切换 BPM</summary>
    public void SetBPM(float newBpm)
    {
        bpm = newBpm;
        _beatDuration = 60f / bpm;
    }

    /// <summary>国风 → 街舞 渐变</summary>
    public void SetStyle(float blend)
    {
        styleBlend = Mathf.Clamp01(blend);
    }
}
