/**
 * work/timeline.json 的类型兜底声明。
 *
 * 背景：`work/` 是流水线中间产物目录，已被 .gitignore 排除，因此新克隆的仓库里
 * 并不存在该文件。而 remotion/src/{Root,NewsVideo,useTitleData}.tsx 在构建期
 * 静态 import 它，若没有本声明，`npm run typecheck` 会直接失败：
 *
 *     src/NewsVideo.tsx(3,22): error TS2307: Cannot find module '../../work/timeline.json'
 *
 * 本文件用 ambient module 声明让 tsc 在文件缺失时仍能通过类型检查；
 * 真实运行前仍需执行流水线生成 work/timeline.json（render.py 会校验并给出提示）。
 *
 * 注意：只解决「类型检查」这一环，不改变运行时的真实数据来源——
 * 渲染时 webpack 仍会解析真实的 work/timeline.json。
 */
declare module "*/work/timeline.json" {
  const data: any;
  export default data;
}
