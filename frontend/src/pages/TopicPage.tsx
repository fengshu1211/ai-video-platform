import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Tag, Tabs, Typography, Button, message } from 'antd'
import { FireOutlined, ThunderboltOutlined, CopyOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

const CATEGORIES = [
  {
    key: 'panel',
    label: '板材选购',
    topics: [
      { title: 'ENF和E0到底差在哪？', desc: '甲醛释放量对比+检测报告怎么认+花木匠ENF板材实测', tag: '科普', hot: true },
      { title: '多层板vs颗粒板vs生态板', desc: '三种板材横评+适用范围+价格对比+定制工厂怎么选', tag: '对比', hot: true },
      { title: 'PET准分子肤感板为什么贵？', desc: '工艺原理+触感对比+应用场景+出厂价说明', tag: '工艺', hot: false },
      { title: '原木碳晶系列有什么优势', desc: '环保性能+防水防潮+安装工艺+适合什么场景', tag: '产品', hot: false },
    ],
  },
  {
    key: 'cabinet',
    label: '定制柜类',
    topics: [
      { title: '一门到顶衣柜真的实用吗', desc: '美观vs变形风险+板材要求+五金搭配+安装注意事项', tag: '避坑', hot: true },
      { title: '橱柜设计最容易踩的3个坑', desc: '台面高度+动线规划+收纳分区+真实案例对比', tag: '避坑', hot: true },
      { title: '酒柜/书柜/阳台柜怎么搭配', desc: '空间利用率+套餐组合+经销商如何给客户推荐', tag: '技巧', hot: false },
      { title: '衣柜内部格局怎么设计最实用', desc: '挂衣区vs叠放区+抽屉布局+功能五金+3种户型方案', tag: '技巧', hot: false },
    ],
  },
  {
    key: 'door',
    label: '木门墙板',
    topics: [
      { title: '烤漆门和免漆门怎么选', desc: '工艺区别+价格差+使用寿命+适用场景+经销商话术', tag: '对比', hot: true },
      { title: '同色墙板配套有多大市场', desc: '木门+墙板+柜体同色定制+出厂价套餐+利润空间', tag: '商机', hot: true },
      { title: '隐形门怎么做才不翻车', desc: '五金件关键+安装细节+常见问题+经销商避坑指南', tag: '避坑', hot: false },
    ],
  },
  {
    key: 'business',
    label: '经销经营',
    topics: [
      { title: '全屋定制门店怎么月入30万', desc: '获客渠道+转化话术+售后服务+复购率提升+圣栎美家案例', tag: '干货', hot: true },
      { title: '抖音获客最有效的3种视频', desc: '产品展示+工艺科普+避坑指南哪种效果好+数据对比', tag: '干货', hot: true },
      { title: '定制工厂怎么选靠谱的板材商', desc: '看授权+看检测报告+看现货+看发货速度+纬臻木业优势', tag: '干货', hot: false },
      { title: '小区团购怎么做才能爆单', desc: '样板间打造+业主群运营+套餐设计+成交话术分享', tag: '技巧', hot: false },
    ],
  },
]

export default function TopicPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('panel')

  const handleCopy = (title: string) => {
    navigator.clipboard.writeText(title)
    message.success('标题已复制')
  }

  const handleUseTopic = (title: string) => {
    navigate('/template', { state: { topicText: title } })
  }

  return (
    <div>
      <Title level={3} style={{ textAlign: 'center', color: '#e2e8f0', marginBottom: 4 }}>
        <FireOutlined style={{ color: '#f59e0b', marginRight: 8 }} />
        行业爆款选题
      </Title>
      <Paragraph style={{ textAlign: 'center', color: '#94a3b8', marginBottom: 24 }}>
        全屋定制行业热门话题，选一个去生成文案
      </Paragraph>

      <Tabs activeKey={activeTab} onChange={setActiveTab} centered
        items={CATEGORIES.map(cat => ({
          key: cat.key,
          label: cat.label,
          children: (
            <Row gutter={[16, 16]}>
              {cat.topics.map((t, i) => (
                <Col xs={24} sm={12} md={6} key={i}>
                  <Card hoverable size="small" style={{ borderRadius: 12, height: '100%', borderColor: 'rgba(148,163,184,0.1)' }}>
                    <div style={{ marginBottom: 8 }}>
                      {t.hot && <Tag color="red" style={{ fontSize: 10 }}>热门</Tag>}
                      <Tag style={{ fontSize: 10 }}>{t.tag}</Tag>
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0', marginBottom: 8 }}>
                      {t.title}
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
                      {t.desc}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <Button size="small" type="primary" icon={<ThunderboltOutlined />}
                        onClick={() => handleUseTopic(t.title)}>
                        去生成
                      </Button>
                      <Button size="small" icon={<CopyOutlined />}
                        onClick={() => handleCopy(t.title)}>
                        复制
                      </Button>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          ),
        }))}
      />
    </div>
  )
}
