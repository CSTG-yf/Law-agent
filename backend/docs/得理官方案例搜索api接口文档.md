案例检索的api：
调用接口示例：
curl -XPOST 'https://openapi.delilegal.com/api/qa/v3/search/queryListCase'
--header "appid: QthdBErlyaYvyXul"
--header "secret: EC5D455E6BD348CE8E18BE05926D2EBE"
5
-d '{
"pageNo": 1,
"pageSize": 3,
"sortField": "correlation",
"sortOrder": "desc",
"condition": {
"caseYearStart": "2020-08-05",
"caseYearEnd": "2023-08-13",
"courtLevelArr": [ "0" ] ,
"keywordArr":[ "上班途中车祸工伤案例" ]
}
}'
其中字段释义：
sortField：指返回结排序两种方式之一，相关性：correlation，裁判时间：time。
sortOrder：排序是升序 asc 还是降序 desc。
condition 属性：
caseYearStart 和 caseYearEnd：案例裁判日期所属的区间（删除这两个值指全部文书）。
courtLevelArr：这是一个法院层级数组，用[ ]包围，可以有多个，其中值的含义：最高法院："0"，
6
高级法院："1"，中级法院："2"，基层人民 法院："3",通常采用2或者3，因为最高法院的案例很少
keywordArr：关键词检索数组[ ]，可以有多个关键词组合如["小产权","买卖合同","效力"]
longText：长文本检索，通常与 keywordArr 二选一，例如"小产权买卖合同是否有效？"，当然这里
通常是在双引号""中输入/ 后会出现前面节点并选中需要的变量，比如 inputtext。
judgementTypeArr：文书类型数组[ ]。判决书："30",裁决书:"31",调解书:"32",决定书:"33",通知书:"34",
其他:"99"


返回结果示例：{
    "success": true,
    "code": 0,
    "msg": "",
    "body": {
        "queryId": "028204150209c7e8361e3ddb43a62837",
        "totalCount": 6,
        "totalPage": 2,
        "data": [
            {
                "title": "江某凰与江西某某建筑劳务有限公司劳动争议一审民事判决书",
                "content": "判罚内容",
                "caseType": "民事案件",
                "cause": "劳动合同纠纷",
                "judgementType": "判决书",
                "judgementDate": "2023-06-25",
                "id": "54663f4658abf9d8ab2d8f43e87d3a0dff96351915b2b9799b52f7b8c5db50d6d43878c5924f0015aff52da779796276",
                "court": "浔阳区人民法院",
                "caseNumber": "（2023）赣0403民初28号",
                "levelOfTrial": "民事一审",
                "publishType": "400",
                "publishTypeName": "普通案例"
            },
            {
                "title": "江某凰与某某建设集团有限公司劳动争议一审民事判决书",
                "content": "判罚内容",
                "caseType": "民事案件",
                "cause": "劳动合同纠纷",
                "judgementType": "判决书",
                "judgementDate": "2022-09-09",
                "id": "84d95d311f2183aeebc49720eec73793d4da1191f983ce250a04cfb60d11e66a0da475507d3a3a211f82723fc10eeb29",
                "court": "浔阳区人民法院",
                "caseNumber": "（2022）赣0403民初1888号",
                "levelOfTrial": "民事一审",
                "publishType": "400",
                "publishTypeName": "普通案例"
            },
            {
                "title": "天津市莱茵环保新技术开发有限公司、衡阳华泰建筑工程有限责任公司郴州分公司等建设工程合同纠纷民事一审民事判决书",
                "content": "",
                "caseType": "民事案件",
                "cause": "建设工程合同纠纷",
                "judgementType": "判决书",
                "judgementDate": "2021-11-30",
                "id": "7dab1c11d0457520b24269890df06b80b58bbb164b6383964301869796156809ddcba9c1229c90654a4cb0fc671f5e95",
                "court": "永兴县人民法院",
                "caseNumber": "（2021）湘1023民初1930号",
                "levelOfTrial": "民事一审",
                "publishType": "400",
                "publishTypeName": "普通案例"
            }
        ]
    }
}