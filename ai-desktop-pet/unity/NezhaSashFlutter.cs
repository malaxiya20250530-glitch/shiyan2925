using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// 混天绫飘动 — 程序化绸缎物理
/// 用骨骼链 + Verlet 积分模拟飘带运动，零 Cloth 组件依赖
/// </summary>
public class NezhaSashFlutter : MonoBehaviour
{
    [Header("飘带骨骼链")]
    public Transform[] sashBones; // 从根到尖排列（自动查找 "Sash_" 前缀）

    [Header("物理参数")]
    public float stiffness = 80f;     // 刚度（越大越硬）
    public float damping = 0.85f;     // 阻尼（0-1, 1=无阻尼）
    public float gravity = 0.3f;      // 重力
    public float windStrength = 1.5f; // 风力
    public float windSpeed = 2f;      // 风速
    public float windTurbulence = 0.4f;
    public float maxStretch = 1.2f;   // 最大拉伸倍数

    [Header("fired_up 增强")]
    public float firedUpWindMultiplier = 3f;
    public float firedUpTurbulence = 2f;

    [Header("碰撞")]
    public LayerMask collisionMask = -1;
    public float collisionRadius = 0.05f;

    private struct BoneState
    {
        public Vector3 position;
        public Vector3 prevPosition;
        public Vector3 baseLocalPos;  // 初始相对父节点的位置
        public Quaternion baseLocalRot;
    }

    private BoneState[] _states;
    private float[] _restLengths;
    private bool _isFiredUp;

    void Start()
    {
        if (sashBones == null || sashBones.Length == 0)
            sashBones = FindSashBones();

        if (sashBones.Length < 2)
        {
            enabled = false;
            return;
        }

        // 记录初始状态
        _states = new BoneState[sashBones.Length];
        _restLengths = new float[sashBones.Length - 1];

        for (int i = 0; i < sashBones.Length; i++)
        {
            _states[i].position = sashBones[i].position;
            _states[i].prevPosition = sashBones[i].position;
            _states[i].baseLocalPos = i == 0
                ? sashBones[i].localPosition
                : sashBones[i].localPosition - sashBones[i - 1].localPosition;
            _states[i].baseLocalRot = sashBones[i].localRotation;

            if (i > 0)
                _restLengths[i - 1] = Vector3.Distance(
                    sashBones[i].position, sashBones[i - 1].position);
        }
    }

    Transform[] FindSashBones()
    {
        var list = new List<Transform>();
        foreach (var t in GetComponentsInChildren<Transform>())
            if (t.name.Contains("Sash") || t.name.Contains("sash"))
                list.Add(t);
        // 按层级深度排序
        list.Sort((a, b) =>
        {
            int da = 0, db = 0;
            var pa = a; while (pa.parent != null) { da++; pa = pa.parent; }
            var pb = b; while (pb.parent != null) { db++; pb = pb.parent; }
            return da.CompareTo(db);
        });
        return list.ToArray();
    }

    void FixedUpdate()
    {
        if (_states == null) return;

        float dt = Time.fixedDeltaTime;
        float mult = _isFiredUp ? firedUpWindMultiplier : 1f;
        float turb = _isFiredUp ? firedUpTurbulence : windTurbulence;

        // Verlet 积分
        for (int i = 1; i < _states.Length; i++)
        {
            Vector3 vel = (_states[i].position - _states[i].prevPosition) * damping;
            Vector3 wind = new Vector3(
                Mathf.PerlinNoise(Time.time * windSpeed, i * 0.5f) - 0.5f,
                Mathf.PerlinNoise(i * 0.5f, Time.time * windSpeed) - 0.5f,
                Mathf.PerlinNoise((Time.time + i) * windSpeed, 0) - 0.3f
            ) * windStrength * mult;

            wind += new Vector3(
                Mathf.Sin(Time.time * 3f + i) * turb,
                Mathf.Cos(Time.time * 2.7f + i) * turb * 0.5f,
                0f
            );

            Vector3 gravityVec = Vector3.down * gravity;
            Vector3 newPos = _states[i].position + vel + (wind + gravityVec) * dt * dt;
            _states[i].prevPosition = _states[i].position;
            _states[i].position = newPos;
        }

        // 距离约束（防止拉伸）
        for (int iter = 0; iter < 5; iter++)
        {
            for (int i = 0; i < _states.Length - 1; i++)
            {
                Vector3 dir = _states[i + 1].position - _states[i].position;
                float dist = dir.magnitude;
                float maxDist = _restLengths[i] * maxStretch;
                if (dist > maxDist || dist < _restLengths[i] * 0.5f)
                {
                    dir = dir.normalized * _restLengths[i];
                    Vector3 center = (_states[i].position + _states[i + 1].position) * 0.5f;
                    _states[i].position = center - dir * 0.5f;
                    _states[i + 1].position = center + dir * 0.5f;
                }
            }
        }

        // 根骨骼固定
        _states[0].position = sashBones[0].position;

        // 应用到 Transform
        for (int i = 1; i < sashBones.Length; i++)
        {
            Vector3 dir = (_states[i].position - _states[i - 1].position).normalized;
            Vector3 baseDir = sashBones[i - 1].TransformDirection(_states[i].baseLocalPos.normalized);
            Quaternion rot = Quaternion.FromToRotation(baseDir, dir);
            sashBones[i].rotation = rot * sashBones[i - 1].rotation * _states[i].baseLocalRot;
        }
    }

    /// <summary>fired_up 时飘带更狂暴</summary>
    public void SetFiredUp(bool active)
    {
        _isFiredUp = active;
    }

    void OnDrawGizmosSelected()
    {
        if (sashBones == null) return;
        Gizmos.color = Color.red;
        for (int i = 0; i < sashBones.Length - 1; i++)
        {
            if (sashBones[i] != null && sashBones[i + 1] != null)
                Gizmos.DrawLine(sashBones[i].position, sashBones[i + 1].position);
        }
    }
}
