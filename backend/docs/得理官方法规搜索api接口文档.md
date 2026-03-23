案例检索的api：
请求示例：
curl -XPOST 'https://openapi.delilegal.com/api/qa/v3/search/queryListLaw'
--header 'Content-Type: application/json'
--header "appid: QthdBErlyaYvyXul"
--header "secret: EC5D455E6BD348CE8E18BE05926D2EBE"
-d '{
"pageNo": 1,
"pageSize": 5,
 "sortField": "correlation",
 "sortOrder": "desc",
9
 "condition": {
 "timeLinessTypeArr": [ "5" ],
 "publishYearStart": "2020-08-01",
 "publishYearEnd": "2024-08-13",
 "activeYearStart": "2020-08-01",
 "activeYearEnd": "2024-08-12",
 "keywords": [ "深圳市房地产相关的法律规定有哪些？" ]
"fieldName": "semantic"
 }


返回示例：{
    "success": true,
    "code": 0,
    "msg": "",
    "body": {
        "data": [
            {
                "activeDate": "2021-10-30",
                "id": "bb598537f9a76c231d71dfb7081eb0659a7d1b454268dde4514f1cfec1be55d9a691fdd5b1bd7e62741edab585ab67068a7a48a01e9df6c2437cde0c56cddf3f",
                "issuedNo": "深圳市第7届人民代表大会常务委员会公告第26号",
                "publishDate": "2021-10-30",
                "publisherName": "广东省深圳市人大及其常委会",
                "title": "深圳经济特区房地产登记条例(2021修正)",
                "timelinessName": "有效",
                "levelName": "经济特区法规",
                "highlights": []
            },
            {
                "activeDate": "2022-03-03",
                "id": "6664d1ff58cd2d2a17a00f4b2101fef93e985f12dfc7ee73c027d2c05d27cd54eec6e6c1e8daf2d3bc192b1a0d36668309e778d9dd85fa47cea0d866246fdc8b",
                "issuedNo": "深圳市人民政府令第342号",
                "publishDate": "2022-03-03",
                "publisherName": "广东省深圳市人民政府",
                "title": "深圳市房地产登记若干规定(试行)(2022修正)",
                "timelinessName": "有效",
                "levelName": "地方政府规章",
                "highlights": []
            },
            {
                "activeDate": "2022-08-01",
                "id": "8fe299dd4cfd3c50b0a53130a579f06cb7ad28cb00a001abcca7d002f472358ad7f23b4e0955b8a7b792164666a17762648a54aadcb560785119fd525c614636",
                "issuedNo": "深圳市第7届人民代表大会常务委员会公告第57号",
                "publishDate": "2022-06-30",
                "publisherName": "广东省深圳市人大及其常委会",
                "title": "深圳经济特区社会建设条例",
                "timelinessName": "有效",
                "levelName": "经济特区法规",
                "highlights": []
            },
            {
                "activeDate": "2023-08-01",
                "id": "73988196b4f684a498a2eb156fa61ec399fe9a9b9944f79a626de55cc92e5fb7eeea0c464e01b39b05a0e347e5dee49c23d97c27912b5bcfc0e17adb32947381",
                "issuedNo": "深圳市人民政府令第354号",
                "publishDate": "2023-06-07",
                "publisherName": "广东省深圳市人民政府",
                "title": "深圳市共有产权住房管理办法",
                "timelinessName": "有效",
                "levelName": "地方政府规章",
                "highlights": []
            },
            {
                "activeDate": "2023-08-01",
                "id": "ccc6619335807fd54631b34916c7517661edea91d7f466d3367f578b65028284ee652a07530c0885b1ba80904616a271b6bbb68a24dc2a6873cec7044822d2ba",
                "issuedNo": "深圳市人民政府令第355号",
                "publishDate": "2023-06-07",
                "publisherName": "广东省深圳市人民政府",
                "title": "深圳市保障性住房规划建设管理办法",
                "timelinessName": "有效",
                "levelName": "地方政府规章",
                "highlights": []
            }
        ],
        "queryId": "f5f49ff7215f734e38100a677c76fefe",
        "totalPage": 2,
        "totalCount": 9
    }
}