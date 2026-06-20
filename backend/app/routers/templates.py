"""全屋定制行业文案模板 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, RewrittenScript
import json

router = APIRouter(prefix="/api/templates", tags=["templates"])

class GenerateReq(BaseModel):
    template_id: str
    fields: dict
    style: str = "随机"

TEMPLATES = [
    {
        "id": "product_showcase",
        "brand": "圣栎美家",
        "name": "产品招商",
        "desc": "面向经销商展示产品，突出合作优势",
        "icon": "gold",
        "structure": [
            {"role": "user", "content": "你是全屋定制生产工厂的招商经理。品牌名：圣栎美家（江山欧派双授权头部生产工厂）。\n\n⚠️ 身份硬性规定：\n• 圣栎美家=江山欧派双授权头部生产工厂（不做板材代理）\n• 禁止写：德国/百隆/海蒂诗/总代理/代理商/山东/川鲁\n• 五金只能写悍高\n\n产品营销角度（根据用户填的产品名称自动选择对应角度）：\n\n【欧派精板系列/ENF级产品】→ 卖品牌+环保\n钩子：'你卖的不是板材，是江山欧派上市公司背书'\n强调：全系ENF级、门墙柜同色、免费设计出图、338元/㎡起\n\n【爆款系列/走量产品】→ 卖性价比\n钩子：'268一平，全屋定制也能走量'\n强调：投影报价无套路、悍高五金、满3㎡送抽屉\n\n【混油柜门】→ 卖色彩+环保\n钩子：'想要莫兰迪色？混油柜门随便挑'\n强调：水性漆无甲醛、可做任何颜色、密度板基材造型强\n\n【贴木皮柜门】→ 卖天然质感\n钩子：'天然木皮vs印刷纹理，客户一摸就知道'\n强调：天然木皮/科技木皮、ENF欧松板基材、华润大宝漆\n\n必选2-3个赋能政策加入文案：精板系列338元/㎡起、爆款系列268元/㎡起、标配悍高五金+PUR封边、门墙柜同色、免费设计出图、创研美家软件、72小时配送、A+品牌成品家具配套。\n\n🔥 **核心差异化卖点（必提）**：圣栎美家为经销商提供AI智能营销系统——选模板、填产品信息、一键生成抖音招商视频，从内容创作到客户引流全链路赋能，经销商不用自己学剪辑、不用花钱请拍摄团队。\n\n口播风格根据产品类型调整：精板系列用专业说服力，爆款系列用热情感染力。"},
            {"role": "user", "content": (
                "为以下全屋定制产品写一段面向经销商的抖音招商口播文案（约150-200字）：\n"
                "产品名称：{product_name}\n"
                "3个卖点：{selling_points}\n"
                "材质/工艺：{material}\n"
                "出厂参考价：{price}\n\n"
                "结构要求：\n"
                "1. 开头用'定制老板看过来'或'经销商注意'引入，直接说产品\n"
                "2. 中间逐一说卖点和材质，强调出厂价优势\n"
                "3. 结尾引导客户在评论区留言索取资料，必须清晰提到品牌名：圣栎美家\n"
                "⚠️ 以下两句必须原文出现（照抄，不准修改）：\n"
                "  第一句：'圣栎美家，江山欧派双授权头部生产工厂'\n"
                "  第二句：'标配悍高阻尼五金'\n"
                "❌ 禁止出现：德国、百隆、海蒂诗、总代理、代理商、山东、川鲁\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "product_name", "label": "产品名称", "placeholder": "如：ENF级实木多层衣柜",
             "options": ["欧派精板ENF级全屋定制柜类", "PET准分子肤感门板", "一门到顶衣柜（ENF实木多层）", "原木碳晶系列柜体", "实木多层烤漆门板", "轩逸系列PET门板"]},
            {"key": "selling_points", "label": "3个卖点", "placeholder": "如：ENF环保、静音阻尼、一门到顶",
             "options": ["ENF环保+静音阻尼+一门到顶", "江山欧派授权+花木匠健康板材+出厂价直供", "防水防潮+不易变形+ENF检测报告背书", "PET肤感工艺+悍高五金+PUR封边", "现货充足+一件代发+16年行业经验"]},
            {"key": "material", "label": "材质/工艺", "placeholder": "如：18mm实木多层板+PET肤感门板",
             "options": ["18mm花木匠ENF实木多层板+PET肤感门板+PUR封边", "18mmENF/LSB双饰面颗粒板+同色门板", "18mmENF欧松板（千年舟澳享板）+PET门板", "原木碳晶板+PET门板+激光封边"]},
            {"key": "price", "label": "参考价格", "placeholder": "如：投影面积338元/㎡（手动填写）"},
        ],
    },
    {
        "id": "craft_knowledge",
        "brand": "圣栎美家",
        "name": "工艺科普",
        "desc": "讲解制作工艺，建立专业信任",
        "icon": "bulb",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的工艺专家。所有文案必须提到品牌名：圣栎美家（江山欧派双授权头部生产工厂）。⚠️圣栎美家是生产工厂，不是板材代理；五金标配悍高。\n\n工艺科普角度（根据用户填的工艺名称自动选择）：\n\n【混油柜门工艺】→ 卖色彩+环保\n角度：'市面上柜门颜色千篇一律？混油柜门想要什么色做什么色'\n强调：水性漆（无甲醛苯系物）、可做任何颜色、密度板基材造型随意\n\n【贴木皮柜门工艺】→ 卖天然质感\n角度：'印刷木纹vs真木皮，客户不一定会说但一定摸得出来'\n强调：天然木皮纹理独一性、科技木皮性价比、ENF欧松板基材不形变\n\n【PUR封边 vs EVA封边】→ 卖工艺差异\n角度：'EVA封边便宜但爱开胶，PUR贵一点但用一辈子'\n强调：PUR防水防潮强度高、胶线细、\n\n【PET肤感工艺】→ 卖触感\n角度：'柜门贴上去像婴儿皮肤一样细腻，这就是PET肤感'\n强调：威仕邦20丝PET膜皮、抗划抗污、同色PVC配套\n\n【实木定向板基材混油】→ 卖稳定性\n角度：'密度板怕潮变形？实木定向板基材混油，稳了'\n强调：欧松板基材+混油饰面、结构稳定、适合湿度变化大的地区\n\n【ENF级环保工艺】→ 卖健康\n角度：'国标最高ENF级，甲醛≤0.025mg/m³，母婴级安全'\n强调：MDI胶/大豆胶、PUR封边锁住甲醛\n\n口播风格：工艺科普用'你知道吗'或'很多人不知道'开头，专业但不枯燥。"},
            {"role": "user", "content": (
                "为以下全屋定制工艺写一段面向经销商的抖音科普文案（约150-200字）：\n"
                "工艺名称：{craft_name}\n"
                "相比其他工艺的优势：{advantages}\n"
                "品质背书：{certificate}\n\n"
                "结构要求：\n"
                "1. 开头用你知道吗或很多人不知道引入\n"
                "2. 解释工艺原理，用生活化比喻\n"
                "3. 对比普通工艺，突出优势\n"
                "4. 结尾用证书/检测报告背书，结尾引导客户在评论区留言索取工艺资料，并提到与圣栎美家合作\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "craft_name", "label": "工艺名称", "placeholder": "如：PUR封边 vs EVA封边",
             "options": ["PUR封边 vs EVA封边（为什么贵还得用）", "PET准分子肤感工艺详解", "ENF级环保工艺全流程", "一门到顶工艺（美观vs变形风险）", "激光封边 vs 普通封边", "实木多层板vs颗粒板vs欧松板怎么选"]},
            {"key": "advantages", "label": "工艺优势", "placeholder": "如：防水防潮、不易开胶、边缘光滑无缝",
             "options": ["防水防潮+不易开胶+边缘光滑无缝", "甲醛释放≤0.025mg/m³+母婴级安全", "板材稳定性好+不易变形+耐刮擦", "出货效率提升30%+客户认可度高"]},
            {"key": "certificate", "label": "品质背书", "placeholder": "如：ENF级环保检测报告、SGS认证",
             "options": ["ENF级环保检测报告（干燥器法+气候箱法）", "SGS认证", "F4星认证", "江山欧派精板自产授权书", "花木匠板材防伪标（隐标+明标+ID卡）"]},
        ],
    },
    {
        "id": "avoid_pitfalls",
        "brand": "圣栎美家",
        "name": "避坑指南",
        "desc": "帮客户避开常见套路，引流到店",
        "icon": "warning",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的资深顾问。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家家居有限公司，是江山欧派双授权头部生产工厂。⚠️注意：圣栎美家是生产工厂，不是板材代理。口播风格犀利直白。"},
            {"role": "user", "content": (
                "为以下全屋定制领域的坑写一段抖音口播避坑文案（约150-200字）：\n"
                "坑的类型：{pitfall_type}\n"
                "正确的避坑方案：{solution}\n\n"
                "结构要求：\n"
                "1. 开头用千万别XXX或你以为捡了便宜制造紧迫感\n"
                "2. 列出最常见的2-3个坑，用真实价格对比\n"
                "3. 给出靠谱的避坑方案\n"
                "4. 结尾引导在评论区留言索取避坑清单，必须提到圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "pitfall_type", "label": "坑的类型", "placeholder": "如：报价套路、板材以次充好、五金件减配",
             "options": ["报价套路（低价引流+后期增项加价）", "板材以次充好（颗粒板冒充多层板）", "五金件减配（杂牌五金半年生锈）", "面积重复计算（不足1㎡按1㎡算）", "口头承诺不写进合同", "E0冒充ENF（检测报告做假）"]},
            {"key": "solution", "label": "避坑方案", "placeholder": "如：认准ENF检测报告、合同注明板材品牌和厚度",
             "options": ["认准ENF检测报告+合同注明板材品牌和厚度", "要求PUR封边+写明五金品牌型号（悍高/百隆）", "签合同前核对投影面积计算方式", "选江山欧派旗下授权经销商（官网可查）", "板材到货验防伪标（隐标+明标+ID卡三重验真）"]},
        ],
    },
    {
        "id": "package_promo",
        "brand": "圣栎美家",
        "name": "套餐推广",
        "desc": "推广套餐活动，引流到店成交",
        "icon": "star",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的销售经理。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家家居有限公司，是江山欧派双授权头部生产工厂。⚠️注意：圣栎美家是生产工厂，不是板材代理。口播风格热情有感染力。"},
            {"role": "user", "content": (
                "为以下全屋定制套餐写一段抖音推广口播文案（约150-200字）：\n"
                "套餐名称：{package_name}\n"
                "套餐内容：{contents}\n"
                "套餐价格：{price}\n"
                "活动有效期：{validity}\n\n"
                "结构要求：\n"
                "1. 开头宣布福利（如重磅消息、仅限X天）\n"
                "2. 说清楚套餐包含什么，强调性价比\n"
                "3. 营造紧迫感（限量/限时）\n"
                "4. 结尾引导在评论区留言索取套餐报价，必须提到圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "package_name", "label": "套餐名称", "placeholder": "如：全屋定制11件套",
             "options": ["极致套餐（11件套8888元）", "简约套餐（11件套9999元）", "亲民套餐（11件套11999元）", "舒适套餐（11件套13999元）", "精装房改造套餐（橱柜+衣柜+玄关柜）"]},
            {"key": "contents", "label": "套餐内容", "placeholder": "如：3米衣柜+2米橱柜+鞋柜+酒柜+书柜+阳台柜",
             "options": ["直排沙发+茶几+1桌4椅+2张床+2个床头柜（11件）", "3米衣柜+2米橱柜+鞋柜+酒柜+书柜+阳台柜", "4米衣柜+3米橱柜+电视柜+餐边柜+玄关柜", "2米衣柜+2.5米橱柜+浴室柜+阳台柜"]},
            {"key": "price", "label": "套餐价格", "placeholder": "如：仅需9999元（原价15800）（手动填写）"},
            {"key": "validity", "label": "有效期", "placeholder": "如：即日起至6月30日，仅限前20名（手动填写）"},
        ],
    },
    {
        "id": "customer_case",
        "brand": "圣栎美家",
        "name": "客户案例",
        "desc": "真实案例打动潜在客户",
        "icon": "camera",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的客服。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家家居有限公司，是江山欧派双授权头部生产工厂。⚠️注意：圣栎美家是生产工厂，不是板材代理。口播风格真诚温暖。"},
            {"role": "user", "content": (
                "为以下全屋定制客户案例写一段抖音口播文案（约150-200字）：\n"
                "案例描述：{case_desc}\n"
                "使用的产品/板材：{products_used}\n\n"
                "结构要求：\n"
                "1. 开头展示改造后的惊艳效果\n"
                "2. 简要说改造前的痛点\n"
                "3. 介绍用了什么产品和板材\n"
                "4. 结尾引导在评论区留言索取同款方案，提到圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "case_desc", "label": "案例描述", "placeholder": "如：成都高新区张女士家89㎡小三房，全屋定制花了3.2万",
             "options": ["成都高新区89㎡小三房全屋定制花了3.2万（欧派精板系列）", "山东济南120㎡精装房改造全屋定制4.5万", "成都双流150㎡大平层全屋定制6.8万（原木碳晶系列）", "重庆渝北90㎡旧房翻新全屋定制2.8万（爆款系列）"]},
            {"key": "products_used", "label": "使用产品/板材", "placeholder": "如：花木匠ENF实木多层板+欧派同款拉手+PET门板",
             "options": ["花木匠ENF实木多层板+悍高五金+PET门板+PUR封边", "花木匠ENF多层板柜体+PET准分子肤感门板+悍高二段力铰链", "原木碳晶系列柜体+PET门板+静音阻尼五金+激光封边", "爆款系列E0颗粒板柜体+ENF/LSB PET门板+百隆铰链"]},
        ],
    },
    {
        "id": "brand_trust",
        "brand": "圣栎美家",
        "name": "行业背书",
        "desc": "展示品牌实力，建立客户信任",
        "icon": "shield",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的市场总监。品牌名：圣栎美家（江山欧派双授权头部生产工厂）。⚠️圣栎美家是生产工厂，不是板材代理。五金标配悍高。\n\n品牌背书角度：\n• 讲产能：成都+临沂两大基地，年产30万方，20+条柜类产线，3+条木门产线\n• 讲授权：江山欧派三授权（精板自产+定制制造+木门），行业稀缺\n• 讲环保：全系ENF级，MDI胶/大豆胶，甲醛≤0.025mg/m³\n• 讲服务：免费设计出图、免费预报价、创研美家软件、72小时配送\n\n口播风格大气自信，用数据和事实说话。"},
            {"role": "user", "content": (
                "为以下品牌写一段抖音口播背书文案（约150-200字）：\n"
                "合作品牌：{brand_name}\n"
                "核心优势：{advantages}\n\n"
                "结构要求：\n"
                "1. 开头亮出品牌身份（我们是江山欧派旗下圣栎美家）\n"
                "2. 用数据和事实说话（授权、检测报告、合作案例）\n"
                "3. 强调服务承诺\n"
                "4. 结尾引导在评论区留言索取合作资料\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "brand_name", "label": "合作品牌", "placeholder": "如：江山欧派授权·花木匠健康板材",
             "options": ["江山欧派（603208）授权·花木匠健康板材", "江山欧派健康整装授权头部工厂"]},
            {"key": "advantages", "label": "核心优势", "placeholder": "如：四川+山东总代理、ENF级环保认证、面向全国定制工厂",
             "options": ["四川成都+山东临沂两大生产基地+定制柜类产线20+条+木门产线3条+年产能30万方", "江山欧派三授权（精板自产+定制制造+木门授权）+ENF+F4星双认证", "现货充足+一件代发+16年行业经验+免费预报价+免费效果图", "面向全国定制工厂+免费寄样品+免费厂内试装"]},
        ],
    },
    {
        "id": "panel_sales",
        "brand": "纬臻木业",
        "name": "板材推广",
        "desc": "推广花木匠健康板材，面向全国定制工厂",
        "icon": "gold",
        "structure": [
            {"role": "user", "content": "你是纬臻木业的板材销售经理。纬臻木业，是江山欧派旗下花木匠健康板材的四川、重庆独家总代。必须提到公司名：纬臻木业和品牌花木匠健康板材。\n\n⚠️ 身份硬性规定：纬臻木业是四川重庆独家总代，不是山东。\n\n板材营销角度（根据用户填的板材类型自动选择）：\n\n【花木匠ENF实木多层板】→ 卖品牌赋能\n钩子：'客户问你家用什么板？花木匠，江山欧派旗下品牌'\n强调：ENF级、上市公司品牌背书、隐标明标防伪、给工厂贴金\n\n【花木匠PET肤感板/准分子】→ 卖门板升级\n钩子：'普通门板升级PET肤感，成本加几块钱，卖相翻一倍'\n强调：威仕邦20丝PET膜皮、同色PVC配套、门墙柜同色打通\n\n【千年舟欧松板/FOSB】→ 卖强度+环保\n钩子：'千年舟品牌+MDI胶ENF级，柜体柜门都能用'\n强调：鲁丽基材、MDI胶、高强度防潮\n\n【原木碳晶系列】→ 卖天然实木\n钩子：'桧木AA直纹直拼，纯正实木，高端看面专用'\n强调：天然桧木、ENF级、高端定制\n\n【爱格板】→ 卖进口品质\n钩子：'爱格板W1000/W980，进口品质，高端客户指定'\n\n赋能政策必选1-2个：采购满2万送创研美家正版、可配套欧派健康木门（精板同色485元/套、轩逸338元/套）解决工厂做木门痛点、满10万享代工厂绿色通道。\n\n🔥 **核心差异化卖点（必提）**：纬臻木业合作伙伴可享AI智能营销系统——选板材模板、填产品参数、一键生成抖音推广视频，帮助定制工厂用最低成本做内容营销。\n\n口播风格专业自信。"},
            {"role": "user", "content": (
                "为花木匠健康板材写一段抖音推广口播文案（约150-200字）：\n"
                "板材类型：{panel_type}\n"
                "环保等级/认证：{eco_level}\n"
                "核心优势：{advantages}\n"
                "面向客户：{target_customers}\n\n"
                "结构要求：\n"
                "1. 开头用'定制工厂老板注意了'或'别再被板材商坑了'引入\n"
                "2. 强调ENF环保等级和检测报告背书\n"
                "3. 说明纬臻木业，是江山欧派旗下花木匠板材的四川、重庆独家总代\n"
                "4. 结尾引导在评论区留言索取板材样品和报价\n"
                "⚠️ 禁止出现以下错误描述：\n"
                "  × 不能说山东总代（纬臻木业是四川、重庆独家总代，山东不在授权范围）\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "panel_type", "label": "板材类型", "placeholder": "如：ENF实木多层板、PET准分子肤感板、原木碳晶系列",
             "options": ["花木匠ENF实木多层板（18mm）", "花木匠ENF/LSB双饰面颗粒板（18mm）", "千年舟ENF/FOSB欧松板（澳享板）", "PET准分子肤感板（ENF/LSB基材）", "原木碳晶系列（桧木AA直纹直拼）", "爱格板W1000/W980（进口）"]},
            {"key": "eco_level", "label": "环保等级/认证", "placeholder": "如：ENF级（甲醛释放≤0.025mg/m³）、F4星认证",
             "options": ["ENF级（甲醛释放≤0.025mg/m³）", "F4星认证", "ENF+F4星双认证（欧派检测报告）", "E0级（气候箱法检测）"]},
            {"key": "advantages", "label": "核心优势", "placeholder": "如：江山欧派授权总代、现货充足、一件代发、16年行业经验",
             "options": ["江山欧派授权总代+现货充足+一件代发+16年行业经验", "四川+山东双仓发货+面向全国定制工厂+免费寄样品", "ENF检测报告+SGS认证+板材防伪标（隐标明标ID卡三重验真）", "出厂价直供+免费预报价+免费效果图+免费收口条"]},
            {"key": "target_customers", "label": "面向客户", "placeholder": "如：全国定制工厂、全屋定制门店、装修公司",
             "options": ["全国定制工厂、全屋定制门店、装修公司", "定制工厂、家具厂、装饰公司、设计师工作室"]},
        ],
    },
    {
        "id": "factory_visit",
        "brand": "纬臻木业",
        "name": "工厂拜访",
        "desc": "拜访使用花木匠板材的客户工厂，帮客户宣传+吸引同行合作",
        "icon": "camera",
        "structure": [
            {"role": "user", "content": "你是纬臻木业的板材销售经理。纬臻木业，是江山欧派旗下花木匠健康板材的四川、重庆独家总代。你的视频文案是去拜访已经采购了花木匠板材的全屋定制工厂客户，一方面帮客户工厂做宣传出镜，一方面向同行展示花木匠板材的实际使用效果。所有文案必须提到花木匠健康板材和纬臻木业。"},
            {"role": "user", "content": (
                "为纬臻木业写一段拜访合作客户工厂的抖音口播文案（约150-200字）：\n"
                "拜访的客户工厂：{factory_name}\n"
                "客户工厂所在地/规模：{factory_info}\n"
                "客户用了哪些花木匠板材：{panels_used}\n"
                "客户工厂的评价/使用效果：{feedback}\n\n"
                "结构要求：\n"
                "1. 开头用'今天我们来到XX工厂'或'带你看一家用花木匠板材的工厂'开场\n"
                "2. 展示客户工厂的生产线和成品效果，帮客户做宣传\n"
                "3. 自然带出客户对花木匠板材的评价\n"
                "4. 结尾引导在评论区留言索取板材样品，必须提到纬臻木业、花木匠\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "factory_name", "label": "拜访的客户工厂名称", "placeholder": "如：成都XX定制家居工厂、山东XX全屋定制",
             "options": ["成都XX定制家居工厂", "山东XX全屋定制工厂", "重庆XX高端定制工厂"]},
            {"key": "factory_info", "label": "工厂所在地/规模", "placeholder": "如：成都双流3000㎡生产基地、月产定制柜500套",
             "options": ["成都双流3000㎡生产基地+月产定制柜500套+20条产线", "山东济南2000㎡工厂+月产300套+全自动产线", "重庆渝北1500㎡工厂+专注高端定制+月产200套"]},
            {"key": "panels_used", "label": "客户用了哪些板材", "placeholder": "如：花木匠ENF实木多层板做柜体+PET准分子肤感板做门板",
             "options": ["花木匠ENF实木多层板做柜体+PET准分子肤感板做门板+PUR封边", "花木匠ENF多层板柜体+ENF/LSB PET门板+悍高五金", "花木匠ENF欧松板（千年舟澳享板）+原木碳晶门板+激光封边"]},
            {"key": "feedback", "label": "客户工厂的评价/使用效果", "placeholder": "如：板材稳定性好不变形、ENF检测客户认可度高、出货效率提升30%",
             "options": ["板材稳定性好不变形+ENF检测客户认可度高+出货效率提升30%", "ENF环保等级客户满意+板材平整度好+花色更新快+发货及时", "用了花木匠板材后客户投诉明显减少+回头客多了"]},
        ],
    },
]


@router.get("")
def list_templates(brand: str = ""):
    result = [
        {"id": t["id"], "name": t["name"], "desc": t["desc"], "icon": t["icon"],
         "brand": t.get("brand", "圣栎美家"), "fields": t["fields"]}
        for t in TEMPLATES
        if not brand or t.get("brand", "圣栎美家") == brand
    ]
    return {"code": 0, "data": result}


@router.post("/generate")
def generate_script(req: GenerateReq, db: Session = Depends(get_db)):
    template_id = req.template_id
    fields = req.fields
    import random as _rnd
    STYLES = [
        {"name": "活泼", "prompt": "用活泼热情的语气，多带口语，像朋友聊天一样。"},
        {"name": "专业", "prompt": "用专业理性的语气，引用数据和标准，像行业顾问在讲解。"},
        {"name": "幽默", "prompt": "用轻松幽默的语气，加一点调侃和自嘲，让人会心一笑又记住要点。"},
    ]
    # 用户选了具体风格就用选中的，否则随机
    if req.style and req.style != "随机":
        style = next((s for s in STYLES if s["name"] == req.style), _rnd.choice(STYLES))
    else:
        style = _rnd.choice(STYLES)

    tmpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if not tmpl:
        return {"code": 1, "message": "模板不存在"}

    messages = []
    for item in tmpl["structure"]:
        content = item["content"]
        if item["role"] == "user":
            content += f"\n口播风格：{style['prompt']}"
        for key, val in fields.items():
            content = content.replace("{" + key + "}", str(val))
        messages.append({"role": item["role"], "content": content})

    from openai import OpenAI
    from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)

    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES):
        r = client.chat.completions.create(
            model="qwen-plus",
            messages=messages,
            temperature=0.8,
            max_tokens=600,
        )
        script = r.choices[0].message.content.strip()

        # 后处理：修正AI常犯的品牌描述错误
        if template_id in ("product_showcase", "craft_knowledge", "avoid_pitfalls",
                           "package_promo", "customer_case", "brand_trust"):
            # 圣栎美家是生产工厂，不是代理
            script = script.replace("山东总代理", "四川生产工厂").replace("双总代理", "生产工厂")
            script = script.replace("川鲁双总代", "生产工厂").replace("川鲁", "")
            script = script.replace("总代理", "生产工厂").replace("代理商", "生产工厂")
            script = script.replace("双总代", "生产工厂")
            # 五金：确保出现悍高（AI常漏）
            script = script.replace("德国百隆", "悍高").replace("德国进口", "悍高")
            script = script.replace("德国静音", "悍高静音").replace("静音阻尼", "悍高静音阻尼")
            script = script.replace("百隆", "悍高")
            if "悍高" not in script and ("阻尼" in script or "铰链" in script):
                script = script.replace("阻尼铰链", "悍高阻尼铰链").replace("阻尼", "悍高阻尼", 1)
            # 确保出现"生产工厂"描述
            if "生产工厂" not in script and "圣栎美家" in script:
                script = script.replace("圣栎美家", "圣栎美家（江山欧派双授权生产工厂）", 1)

        elif template_id in ("panel_sales", "factory_visit"):
            # 纬臻木业是四川重庆独家总代，不是山东
            script = script.replace("山东总代理", "独家总代理").replace("山东", "")
            script = script.replace("两省的", "川渝").replace("两省", "川渝")

        # 通用修正
        script = script.replace("德国品牌", "悍高").replace("德国五金", "悍高五金")
        break

    record = RewrittenScript(
        original_text=json.dumps(fields, ensure_ascii=False),
        rewritten_text=script,
        style=template_id,
        word_count=len(script),
        source_type="template",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"code": 0, "data": {"script_id": record.id, "text": script, "style": style["name"]}}
