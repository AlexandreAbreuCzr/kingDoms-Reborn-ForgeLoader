#pragma once
#include <string>
#include <vector>
#include <cstdint>
#include <stdexcept>

namespace krphoto {
constexpr size_t MaxJpeg = 8192, MaxToken = 12000, MaxFallback = 128;
inline std::string base64(const std::vector<uint8_t>& data) {
    const char* alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    for(size_t i=0;i<data.size();i+=3){
        uint32_t v=uint32_t(data[i])<<16;
        if(i+1<data.size())v|=uint32_t(data[i+1])<<8;
        if(i+2<data.size())v|=data[i+2];
        out+=alphabet[(v>>18)&63];out+=alphabet[(v>>12)&63];
        out+=i+1<data.size()?alphabet[(v>>6)&63]:'=';
        out+=i+2<data.size()?alphabet[v&63]:'=';
    }
    return out;
}
inline bool unbase64(const std::wstring& text,std::vector<uint8_t>& out,size_t limit) {
    out.clear();
    if(text.empty() || text.size()%4 || text.size()>((limit+2)/3)*4)return false;
    auto value=[](wchar_t c)->int{
        if(c>='A'&&c<='Z')return c-'A';if(c>='a'&&c<='z')return c-'a'+26;
        if(c>='0'&&c<='9')return c-'0'+52;if(c=='+')return 62;if(c=='/')return 63;return -1;
    };
    for(size_t i=0;i<text.size();i+=4){
        int a=value(text[i]),b=value(text[i+1]),c=value(text[i+2]),d=value(text[i+3]);
        bool p2=text[i+2]=='=',p3=text[i+3]=='=';
        if(a<0||b<0||(!p2&&c<0)||(!p3&&d<0)|| (p2&&!p3) || ((p2||p3)&&i+4!=text.size()))return false;
        if((p2&&(b&15))||(!p2&&p3&&(c&3)))return false;
        uint32_t v=(a<<18)|(b<<12)|((p2?0:c)<<6)|(p3?0:d);
        out.push_back(uint8_t(v>>16));if(!p2)out.push_back(uint8_t(v>>8));if(!p3)out.push_back(uint8_t(v));
        if(out.size()>limit)return false;
    }
    return true;
}
struct Photo { bool marked=false,valid=false;std::wstring fallback;std::vector<uint8_t> jpeg; };
inline bool valid_name(const std::wstring& value){
    if(value.empty()||value.size()>MaxFallback)return false;
    for(size_t i=0;i<value.size();++i){auto c=uint16_t(value[i]);if(c<32)return false;
        if(c>=0xd800&&c<=0xdbff){if(++i>=value.size()||uint16_t(value[i])<0xdc00||uint16_t(value[i])>0xdfff)return false;}
        else if(c>=0xdc00&&c<=0xdfff)return false;
    }return true;
}
inline Photo decode(const std::wstring& token){
    Photo p;p.marked=token.rfind(L"KRPM1|",0)==0;
    if(!p.marked||token.size()>MaxToken)return p;
    size_t split=token.find(L'|',6);if(split==std::wstring::npos)return p;
    std::vector<uint8_t> raw;
    if(!unbase64(token.substr(6,split-6),raw,MaxFallback*2)||raw.size()%2)return p;
    for(size_t i=0;i<raw.size();i+=2)p.fallback.push_back(wchar_t(raw[i]|(raw[i+1]<<8)));
    if(!valid_name(p.fallback)){p.fallback.clear();return p;}
    if(!unbase64(token.substr(split+1),p.jpeg,MaxJpeg)||p.jpeg.size()<4||p.jpeg[0]!=255||p.jpeg[1]!=216){p.jpeg.clear();return p;}
    p.valid=true;return p;
}
inline std::wstring encode(const std::wstring& fallback,const std::vector<uint8_t>& jpeg){
    if(!valid_name(fallback)||jpeg.size()<4||jpeg.size()>MaxJpeg||jpeg[0]!=255||jpeg[1]!=216)throw std::invalid_argument("photo limits");
    std::vector<uint8_t> name;for(auto c:fallback){name.push_back(uint8_t(c));name.push_back(uint8_t(uint16_t(c)>>8));}
    std::string ascii="KRPM1|"+base64(name)+"|"+base64(jpeg);
    if(ascii.size()>MaxToken)throw std::invalid_argument("token too large");
    return std::wstring(ascii.begin(),ascii.end());
}
}
